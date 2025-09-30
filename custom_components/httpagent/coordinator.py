"""Data coordinator for HTTP Agent."""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import timedelta
from typing import Any, Dict

import aiohttp
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_URL
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.template import Template
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    DOMAIN,
    CONF_SSL_VERIFY,
    CONF_TIMEOUT,
    CONF_METHOD,
    CONF_PAYLOAD,
    CONF_QUERYSTRING,
    DEFAULT_TIMEOUT,
    DEFAULT_SSL_VERIFY,
    STATE_OK,
    STATE_ERROR,
    STATE_TIMEOUT,
    SERVICE_URL,
    SERVICE_METHOD,
    SERVICE_PAYLOAD,
    SERVICE_HEADERS,
    SERVICE_TIMEOUT,
    SERVICE_SSL_VERIFY,
    SERVICE_QUERYSTRING,
)

_LOGGER = logging.getLogger(__name__)


class HTTPAgentCoordinator(DataUpdateCoordinator):
    """Class to manage fetching data from HTTP endpoints."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize."""
        self.hass = hass
        self.entry = entry
        self._session: aiohttp.ClientSession | None = None
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=60),  # Default, overridden per sensor
        )

    @property
    def session(self) -> aiohttp.ClientSession:
        """Get aiohttp session."""
        if self._session is None or self._session.closed:
            connector = aiohttp.TCPConnector(
                limit=100,
                limit_per_host=30,
                enable_cleanup_closed=True,
            )
            timeout = aiohttp.ClientTimeout(total=DEFAULT_TIMEOUT)
            self._session = aiohttp.ClientSession(
                connector=connector,
                timeout=timeout,
            )
        return self._session

    async def _async_update_data(self) -> Dict[str, Any]:
        """Update data via library."""
        # This method is used by the base coordinator class
        # Individual sensors will have their own update methods
        return {}

    async def async_shutdown(self) -> None:
        """Close the session."""
        if self._session and not self._session.closed:
            await self._session.close()

    def _render_template(self, template_str: str, variables: Dict[str, Any] | None = None) -> str:
        """Render a template with the given variables."""
        if not template_str:
            return ""
        
        try:
            template = Template(template_str, self.hass)
            return template.async_render(variables or {})
        except Exception as err:
            _LOGGER.warning("Failed to render template '%s': %s", template_str, err)
            return template_str

    async def make_http_request(
        self,
        url: str,
        method: str = "GET",
        payload: str | None = None,
        headers: Dict[str, str] | None = None,
        timeout: int = DEFAULT_TIMEOUT,
        ssl_verify: bool = DEFAULT_SSL_VERIFY,
        querystring: str | None = None,
        variables: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        """Make an HTTP request."""
        try:
            # Render templates
            rendered_url = self._render_template(url, variables)
            rendered_payload = self._render_template(payload or "", variables)
            rendered_querystring = self._render_template(querystring or "", variables)
            
            # Build the full URL with query parameters
            full_url = rendered_url
            if rendered_querystring:
                separator = "&" if "?" in full_url else "?"
                full_url = f"{full_url}{separator}{rendered_querystring}"
            
            # Prepare request data
            request_kwargs = {
                "method": method.upper(),
                "url": full_url,
                "timeout": aiohttp.ClientTimeout(total=timeout),
                "ssl": ssl_verify,
            }
            
            # Add headers
            if headers:
                rendered_headers = {}
                for key, value in headers.items():
                    rendered_headers[key] = self._render_template(value, variables)
                request_kwargs["headers"] = rendered_headers
            
            # Add payload for methods that support it
            if method.upper() in ["POST", "PUT", "PATCH"] and rendered_payload:
                try:
                    # Try to parse as JSON first
                    json_payload = json.loads(rendered_payload)
                    request_kwargs["json"] = json_payload
                except json.JSONDecodeError:
                    # If not JSON, send as text
                    request_kwargs["data"] = rendered_payload
                    if "headers" not in request_kwargs:
                        request_kwargs["headers"] = {}
                    request_kwargs["headers"]["Content-Type"] = "text/plain"
            
            _LOGGER.debug("Making HTTP request: %s %s", method.upper(), full_url)
            
            async with self.session.request(**request_kwargs) as response:
                response_text = await response.text()
                
                # Try to parse response as JSON
                try:
                    response_data = await response.json()
                except (aiohttp.ContentTypeError, json.JSONDecodeError):
                    response_data = response_text
                
                return {
                    "status_code": response.status,
                    "state": STATE_OK if 200 <= response.status < 300 else STATE_ERROR,
                    "response": response_data,
                    "response_text": response_text,
                    "headers": dict(response.headers),
                    "url": full_url,
                    "method": method.upper(),
                }
                
        except asyncio.TimeoutError:
            _LOGGER.warning("Timeout making HTTP request to %s", url)
            return {
                "status_code": None,
                "state": STATE_TIMEOUT,
                "response": None,
                "response_text": "",
                "headers": {},
                "url": url,
                "method": method.upper(),
                "error": "Timeout",
            }
        except Exception as err:
            _LOGGER.error("Error making HTTP request to %s: %s", url, err)
            return {
                "status_code": None,
                "state": STATE_ERROR,
                "response": None,
                "response_text": "",
                "headers": {},
                "url": url,
                "method": method.upper(),
                "error": str(err),
            }

    async def handle_service_call(self, call: ServiceCall, method: str | None = None) -> None:
        """Handle service call."""
        url = call.data.get(SERVICE_URL)
        if not url:
            raise HomeAssistantError("URL is required")
        
        service_method = method or call.data.get(SERVICE_METHOD, "GET")
        payload = call.data.get(SERVICE_PAYLOAD)
        headers = call.data.get(SERVICE_HEADERS, {})
        timeout = call.data.get(SERVICE_TIMEOUT, DEFAULT_TIMEOUT)
        ssl_verify = call.data.get(SERVICE_SSL_VERIFY, DEFAULT_SSL_VERIFY)
        querystring = call.data.get(SERVICE_QUERYSTRING)
        
        # Get all available variables for template rendering
        variables = dict(call.data)
        variables.update({
            "states": self.hass.states,
            "now": self.hass.helpers.template.now(),
        })
        
        result = await self.make_http_request(
            url=url,
            method=service_method,
            payload=payload,
            headers=headers,
            timeout=timeout,
            ssl_verify=ssl_verify,
            querystring=querystring,
            variables=variables,
        )
        
        # Fire an event with the result
        self.hass.bus.async_fire(
            f"{DOMAIN}_response",
            {
                "service": call.service,
                "data": call.data,
                "result": result,
            }
        )
        
        _LOGGER.info(
            "HTTP %s request to %s completed with status %s",
            service_method,
            url,
            result.get("status_code", "unknown"),
        )