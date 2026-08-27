"""Low level HTTP client used by both the config flow and the coordinator."""

from __future__ import annotations

import asyncio
from functools import partial
from http import HTTPStatus
import logging
from typing import Any

import aiohttp

from homeassistant.const import (
    CONF_API_KEY,
    CONF_HEADERS,
    CONF_METHOD,
    CONF_PASSWORD,
    CONF_PAYLOAD,
    CONF_TIMEOUT,
    CONF_TOKEN,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, TemplateError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.template import Template

from .const import (
    AUTH_API_KEY,
    AUTH_BASIC,
    AUTH_BEARER,
    CONF_API_KEY_HEADER,
    CONF_AUTH_TYPE,
    CONF_CONTENT_TYPE,
    CONF_FOLLOW_REDIRECTS,
    CONF_RESPONSE_FORMAT,
    CONF_RETRIES,
    DEFAULT_API_KEY_HEADER,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_FOLLOW_REDIRECTS,
    DEFAULT_METHOD,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    FORMAT_AUTO,
    METHOD_HEAD,
    METHODS_WITH_BODY,
    RETRY_DELAY,
)
from .parser import ParsedResponse

_LOGGER = logging.getLogger(__name__)

# Response headers that must never reach logs or diagnostics.
SENSITIVE_HEADERS = frozenset(
    {"authorization", "proxy-authorization", "cookie", "set-cookie"}
)


class HttpAgentError(HomeAssistantError):
    """Base error for the HTTP Agent integration."""


class CannotConnect(HttpAgentError):
    """The endpoint could not be reached."""


class InvalidAuth(HttpAgentError):
    """The endpoint rejected the supplied credentials."""


class InvalidResponse(HttpAgentError):
    """The endpoint answered with an unusable status code."""

    def __init__(self, status: int) -> None:
        """Store the offending status code."""
        super().__init__(f"Endpoint returned HTTP {status}")
        self.status = status


class EmptyResponse(HttpAgentError):
    """The endpoint answered with an empty body."""


def build_request_headers(config: dict[str, Any]) -> dict[str, str]:
    """Return the full header set, combining the auth preset and custom headers."""
    headers: dict[str, str] = {}

    auth_type = config.get(CONF_AUTH_TYPE)
    if auth_type == AUTH_BEARER and (token := config.get(CONF_TOKEN)):
        headers["Authorization"] = f"Bearer {token}"
    elif auth_type == AUTH_API_KEY and (api_key := config.get(CONF_API_KEY)):
        headers[config.get(CONF_API_KEY_HEADER) or DEFAULT_API_KEY_HEADER] = api_key

    headers.update(config.get(CONF_HEADERS) or {})
    return headers


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    """Return ``headers`` with credential-bearing values masked."""
    return {
        key: "**REDACTED**" if key.lower() in SENSITIVE_HEADERS else value
        for key, value in headers.items()
    }


async def async_request(
    hass: HomeAssistant, config: dict[str, Any], *, allow_empty: bool = False
) -> ParsedResponse:
    """Request the endpoint, retrying transient failures as configured."""
    attempts = max(1, int(config.get(CONF_RETRIES, DEFAULT_RETRIES)) + 1)

    for attempt in range(1, attempts + 1):
        try:
            return await _async_single_request(hass, config, allow_empty=allow_empty)
        except InvalidAuth:
            # Credentials will not become valid by trying again.
            raise
        except (CannotConnect, InvalidResponse, EmptyResponse) as err:
            if attempt == attempts:
                raise
            _LOGGER.debug("Attempt %s/%s failed: %s", attempt, attempts, err)
            await asyncio.sleep(RETRY_DELAY)

    raise CannotConnect("Request failed")  # pragma: no cover - loop always returns


async def _async_single_request(
    hass: HomeAssistant, config: dict[str, Any], *, allow_empty: bool = False
) -> ParsedResponse:
    """Perform one request against the configured endpoint and parse the result."""
    method = (config.get(CONF_METHOD) or DEFAULT_METHOD).upper()
    timeout = config.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
    verify_ssl = config.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)

    url = _render(hass, config[CONF_URL])
    headers = {
        key: _render(hass, value)
        for key, value in build_request_headers(config).items()
    }

    auth: aiohttp.BasicAuth | None = None
    if config.get(CONF_AUTH_TYPE) == AUTH_BASIC:
        auth = aiohttp.BasicAuth(
            config.get(CONF_USERNAME, ""), config.get(CONF_PASSWORD, "")
        )

    kwargs: dict[str, Any] = {
        "headers": headers,
        "auth": auth,
        "timeout": aiohttp.ClientTimeout(total=timeout),
        "allow_redirects": config.get(CONF_FOLLOW_REDIRECTS, DEFAULT_FOLLOW_REDIRECTS),
    }

    if method in METHODS_WITH_BODY and (payload := config.get(CONF_PAYLOAD)):
        content_type = config.get(CONF_CONTENT_TYPE) or DEFAULT_CONTENT_TYPE
        headers.setdefault("Content-Type", content_type)
        kwargs["data"] = _render(hass, payload).encode("utf-8")

    session = async_get_clientsession(hass, verify_ssl=verify_ssl)

    try:
        async with session.request(method, url, **kwargs) as response:
            text = await response.text()
            status = response.status
            response_headers = {
                key.lower(): value for key, value in response.headers.items()
            }
    except TimeoutError as err:
        raise CannotConnect(f"Timeout while contacting {url}") from err
    except aiohttp.ClientError as err:
        raise CannotConnect(f"Error contacting {url}: {err}") from err
    except asyncio.CancelledError:
        raise
    except Exception as err:
        raise CannotConnect(f"Unexpected error contacting {url}: {err}") from err

    _LOGGER.debug("%s %s responded with HTTP %s", method, url, status)

    if status in (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN):
        raise InvalidAuth(f"Endpoint returned HTTP {status}")
    if status >= HTTPStatus.BAD_REQUEST:
        raise InvalidResponse(status)
    if not text.strip() and method != METHOD_HEAD and not allow_empty:
        raise EmptyResponse(f"Endpoint returned an empty body with HTTP {status}")

    # Parsing large HTML or XML bodies is CPU bound, keep it off the event loop.
    return await hass.async_add_executor_job(
        partial(
            ParsedResponse.parse,
            text=text,
            status=status,
            headers=response_headers,
            response_format=config.get(CONF_RESPONSE_FORMAT) or FORMAT_AUTO,
        )
    )


def _render(hass: HomeAssistant, value: str) -> str:
    """Render a Home Assistant template, falling back to the literal string."""
    if not value or "{" not in value:
        return value
    try:
        return Template(value, hass).async_render(parse_result=False)
    except TemplateError as err:
        _LOGGER.warning("Could not render template %r: %s", value, err)
        return value
