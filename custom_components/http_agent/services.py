"""Actions for the HTTP Agent integration.

``http_agent.request`` lets an automation or script call an HTTP endpoint on
demand and use the answer in a later step. Values are extracted with the same
path syntax as the sensors, so the returned data is normalised the same way.
"""

from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

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
from homeassistant.core import (
    HomeAssistant,
    ServiceCall,
    ServiceResponse,
    SupportsResponse,
    callback,
)
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .api import (
    CannotConnect,
    InvalidAuth,
    InvalidResponse,
    async_request,
    redact_headers,
)
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_SELECT,
    CONF_API_KEY_HEADER,
    CONF_AUTH_TYPE,
    CONF_CONTENT_TYPE,
    CONF_FOLLOW_REDIRECTS,
    CONF_RESPONSE_FORMAT,
    CONF_RETRIES,
    CONTENT_TYPES,
    DOMAIN,
    FORMAT_JSON,
    HTTP_METHODS,
    MAX_RETRIES,
    MAX_TIMEOUT,
    METHOD_GET,
    MIN_TIMEOUT,
    RESPONSE_FORMATS,
    SERVICE_REQUEST,
)

# Connection and credential settings an existing endpoint contributes.
_INHERITED = (
    CONF_API_KEY,
    CONF_API_KEY_HEADER,
    CONF_AUTH_TYPE,
    CONF_FOLLOW_REDIRECTS,
    CONF_HEADERS,
    CONF_PASSWORD,
    CONF_RESPONSE_FORMAT,
    CONF_RETRIES,
    CONF_TIMEOUT,
    CONF_TOKEN,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)

# What is sent is decided by the call alone, never by the stored endpoint.
_NEVER_INHERITED = (CONF_CONTENT_TYPE, CONF_PAYLOAD)

# Inherited from the endpoint, but the call may override them.
_OVERRIDABLE = (
    CONF_RESPONSE_FORMAT,
    CONF_RETRIES,
    CONF_TIMEOUT,
    CONF_VERIFY_SSL,
)

REQUEST_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional(CONF_URL): cv.string,
        vol.Optional(CONF_METHOD, default=METHOD_GET): vol.All(
            vol.Upper, vol.In(HTTP_METHODS)
        ),
        vol.Optional(CONF_HEADERS): vol.Schema({cv.string: cv.string}),
        vol.Optional(CONF_PAYLOAD): cv.string,
        vol.Optional(ATTR_SELECT): vol.Schema({cv.string: cv.string}),
        vol.Optional(CONF_CONTENT_TYPE): vol.In(CONTENT_TYPES),
        vol.Optional(CONF_RESPONSE_FORMAT): vol.In(RESPONSE_FORMATS),
        vol.Optional(CONF_TIMEOUT): vol.All(
            vol.Coerce(int), vol.Range(min=MIN_TIMEOUT, max=MAX_TIMEOUT)
        ),
        vol.Optional(CONF_VERIFY_SSL): cv.boolean,
        vol.Optional(CONF_RETRIES): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=MAX_RETRIES)
        ),
    }
)


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the integration actions."""
    hass.services.async_register(
        DOMAIN,
        SERVICE_REQUEST,
        _async_handle_request,
        schema=REQUEST_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


async def _async_handle_request(call: ServiceCall) -> ServiceResponse:
    """Perform one request and return the normalised result."""
    config = _build_config(call.hass, call.data)

    try:
        response = await async_request(call.hass, config, allow_empty=True)
    except InvalidAuth as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN, translation_key="invalid_auth"
        ) from err
    except InvalidResponse as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="bad_status",
            translation_placeholders={"status": str(err.status)},
        ) from err
    except CannotConnect as err:
        raise HomeAssistantError(
            translation_domain=DOMAIN,
            translation_key="cannot_connect",
            translation_placeholders={"error": str(err)},
        ) from err

    selectors: dict[str, str] = call.data.get(ATTR_SELECT) or {}
    return {
        "status": response.status,
        "format": response.format,
        "headers": redact_headers(response.headers),
        "values": {name: response.extract(path) for name, path in selectors.items()},
        "content": (
            response.json_data if response.format == FORMAT_JSON else response.text
        ),
    }


def _build_config(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """Combine the referenced endpoint with the settings given in the call."""
    config: dict[str, Any] = {}

    if entry_id := data.get(ATTR_CONFIG_ENTRY_ID):
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is None or entry.domain != DOMAIN:
            raise ServiceValidationError(
                translation_domain=DOMAIN,
                translation_key="unknown_endpoint",
                translation_placeholders={"target": entry_id},
            )
        config = {key: value for key, value in entry.data.items() if key in _INHERITED}

    if url := data.get(CONF_URL):
        config[CONF_URL] = _resolve_url(config.get(CONF_URL), url)
    if not config.get(CONF_URL):
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="missing_url"
        )

    headers = dict(config.get(CONF_HEADERS) or {})
    headers.update(data.get(CONF_HEADERS) or {})
    config[CONF_HEADERS] = headers

    config[CONF_METHOD] = data[CONF_METHOD]
    for key in _NEVER_INHERITED:
        config.pop(key, None)
    for key in (*_NEVER_INHERITED, *_OVERRIDABLE):
        if key in data:
            config[key] = data[key]

    return config


def _resolve_url(base: str | None, url: str) -> str:
    """Resolve a path-only URL against the host of the referenced endpoint."""
    if base and url.startswith("/"):
        parsed = urlparse(base)
        return f"{parsed.scheme}://{parsed.netloc}{url}"
    return url
