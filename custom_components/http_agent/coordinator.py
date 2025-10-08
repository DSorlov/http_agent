"""Data update coordinator for HTTP Agent."""

from __future__ import annotations

import asyncio
from datetime import timedelta
import json
import logging
from typing import Any
from xml.etree import ElementTree as ET

import aiohttp
from bs4 import BeautifulSoup

from homeassistant.core import HomeAssistant
from homeassistant.helpers.template import Template
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CONF_CONTENT_TYPE,
    CONF_HEADERS,
    CONF_INTERVAL,
    CONF_METHOD,
    CONF_PAYLOAD,
    CONF_SENSOR_COLOR,
    CONF_SENSOR_DEVICE_CLASS,
    CONF_SENSOR_ICON,
    CONF_SENSOR_NAME,
    CONF_SENSOR_STATE,
    CONF_SENSOR_TYPE,
    CONF_SENSOR_UNIT,
    CONF_SENSORS,
    CONF_TIMEOUT,
    CONF_TRACKER_LATITUDE,
    CONF_TRACKER_LOCATION_NAME,
    CONF_TRACKER_LONGITUDE,
    CONF_TRACKER_SOURCE_TYPE,
    CONF_URL,
    CONF_VERIFY_SSL,
    DEFAULT_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class HTTPResponse:
    """Custom response class for template access."""

    def __init__(self, text: str, status: int, headers: dict):
        """Initialize the response."""
        self.text = text
        self.status = status
        self.headers = headers

        # Try to parse as JSON
        try:
            self.json = json.loads(text)
        except (json.JSONDecodeError, TypeError):
            self.json = None

        # Parse as XML/HTML
        try:
            self.soup = BeautifulSoup(text, "lxml")
            self.xml = ET.fromstring(text)
        except Exception:
            self.soup = None
            self.xml = None


class HTTPAgentCoordinator(DataUpdateCoordinator):
    """HTTP Agent data update coordinator."""

    def __init__(self, hass: HomeAssistant, entry_data: dict) -> None:
        """Initialize the coordinator."""
        self.hass = hass
        self.entry_data = entry_data

        # Configuration
        self.url = entry_data[CONF_URL]
        self.method = entry_data[CONF_METHOD]
        self.timeout = entry_data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
        self.verify_ssl = entry_data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL)
        self.headers = {h["key"]: h["value"] for h in entry_data.get(CONF_HEADERS, [])}
        self.payload = entry_data.get(CONF_PAYLOAD, "")
        self.content_type = entry_data.get(CONF_CONTENT_TYPE, "application/json")
        self.sensors_config = entry_data[CONF_SENSORS]

        # Session
        self.session = None

        # Update interval
        update_interval = timedelta(
            seconds=entry_data.get(CONF_INTERVAL, DEFAULT_INTERVAL)
        )

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from HTTP endpoint."""
        if not self.session:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = aiohttp.TCPConnector(ssl=self.verify_ssl)
            self.session = aiohttp.ClientSession(timeout=timeout, connector=connector)

        try:
            # Render templates in URL, headers, and payload
            rendered_url = self._render_template(self.url)
            rendered_headers = self.headers.copy()
            for key, value in rendered_headers.items():
                rendered_headers[key] = self._render_template(value)

            rendered_payload = (
                self._render_template(self.payload) if self.payload else None
            )

            # Set content type header if we have a payload
            if rendered_payload and self.content_type:
                rendered_headers["Content-Type"] = self.content_type

            # Make HTTP request
            kwargs = {
                "url": rendered_url,
                "headers": rendered_headers,
            }

            if rendered_payload:
                if self.content_type == "application/json":
                    try:
                        kwargs["json"] = json.loads(rendered_payload)
                    except json.JSONDecodeError:
                        kwargs["data"] = rendered_payload
                else:
                    kwargs["data"] = rendered_payload

            async with self.session.request(self.method, **kwargs) as response:
                response_text = await response.text()

                _LOGGER.debug(
                    "HTTP request to %s returned status %s",
                    rendered_url,
                    response.status,
                )

                # Create custom response object for templates
                http_response = HTTPResponse(
                    text=response_text,
                    status=response.status,
                    headers=dict(response.headers),
                )

                # Extract sensor data
                sensor_data = {}
                for sensor_config in self.sensors_config:
                    sensor_name = sensor_config[CONF_SENSOR_NAME]
                    sensor_type = sensor_config.get(CONF_SENSOR_TYPE, "sensor")

                    # Base sensor values
                    sensor_values = {
                        "type": sensor_type,
                        "state": self._extract_value_auto(
                            http_response, sensor_config.get(CONF_SENSOR_STATE, "")
                        ),
                        "icon": self._extract_value_auto(
                            http_response, sensor_config.get(CONF_SENSOR_ICON, "")
                        ),
                        "color": self._extract_value_auto(
                            http_response, sensor_config.get(CONF_SENSOR_COLOR, "")
                        ),
                        "device_class": sensor_config.get(CONF_SENSOR_DEVICE_CLASS, ""),
                        "unit": sensor_config.get(CONF_SENSOR_UNIT, ""),
                    }

                    # Add device tracker specific data
                    if sensor_type == "device_tracker":
                        sensor_values.update(
                            {
                                "latitude": self._extract_value_auto(
                                    http_response,
                                    sensor_config.get(CONF_TRACKER_LATITUDE, ""),
                                ),
                                "longitude": self._extract_value_auto(
                                    http_response,
                                    sensor_config.get(CONF_TRACKER_LONGITUDE, ""),
                                ),
                                "location_name": self._extract_value_auto(
                                    http_response,
                                    sensor_config.get(CONF_TRACKER_LOCATION_NAME, ""),
                                ),
                                "source_type": sensor_config.get(
                                    CONF_TRACKER_SOURCE_TYPE, "gps"
                                ),
                            }
                        )

                    sensor_data[sensor_name] = sensor_values

                return sensor_data

        except asyncio.TimeoutError as err:
            raise UpdateFailed(f"Timeout while fetching data: {err}") from err
        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error fetching data: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

    def _render_template(self, template_string: str) -> str:
        """Render a template string."""
        if not template_string:
            return template_string

        try:
            template = Template(template_string, self.hass)
            return template.async_render()
        except Exception as err:
            _LOGGER.warning("Error rendering template '%s': %s", template_string, err)
            return template_string

    def _extract_value_auto(self, response: HTTPResponse, selector: str) -> Any:
        """Extract value from response using auto-detected method."""
        if not selector:
            return None

        # Try different extraction methods in order of preference
        methods_to_try = []

        # Determine extraction methods based on content type and available data
        content_type = response.headers.get("content-type", "").lower()

        if "json" in content_type or response.json is not None:
            methods_to_try.append(("json", self._extract_json_value, response.json))

        if "xml" in content_type or response.xml is not None:
            methods_to_try.append(("xml", self._extract_xml_value, response.xml))

        if "html" in content_type or response.soup is not None:
            methods_to_try.append(("css", self._extract_css_value, response.soup))

        # If no content type match, try all available methods
        if not methods_to_try:
            if response.json is not None:
                methods_to_try.append(("json", self._extract_json_value, response.json))
            if response.xml is not None:
                methods_to_try.append(("xml", self._extract_xml_value, response.xml))
            if response.soup is not None:
                methods_to_try.append(("css", self._extract_css_value, response.soup))

        # Try each method until one succeeds
        for method_name, extract_func, data in methods_to_try:
            if data is not None:
                try:
                    result = extract_func(data, selector)
                    if result is not None:
                        _LOGGER.debug(
                            "Successfully extracted value using %s method with selector '%s': %s",
                            method_name,
                            selector,
                            result,
                        )
                        return result
                except Exception as err:
                    _LOGGER.debug(
                        "Failed to extract value using %s method with selector '%s': %s",
                        method_name,
                        selector,
                        err,
                    )
                    continue

        _LOGGER.warning(
            "Could not extract value with selector '%s' using any available method",
            selector,
        )
        return None

    def _extract_json_value(self, json_data: dict | list, path: str) -> Any:
        """Extract value from JSON using JSONPath-like syntax."""
        if not json_data:
            return None

        parts = path.split(".")
        current = json_data

        for part in parts:
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, list):
                try:
                    index = int(part)
                    current = current[index]
                except (ValueError, IndexError):
                    return None
            else:
                return None

            if current is None:
                return None

        return current

    def _extract_xml_value(self, xml_data: ET.Element, xpath: str) -> Any:
        """Extract value from XML using XPath."""
        if xml_data is None:
            return None

        try:
            elements = xml_data.findall(xpath)
            if elements:
                return elements[0].text
        except Exception:
            pass

        return None

    def _extract_css_value(self, soup: BeautifulSoup, selector: str) -> Any:
        """Extract value from HTML using CSS selector."""
        if soup is None:
            return None

        try:
            element = soup.select_one(selector)
            if element:
                return element.get_text(strip=True)
        except Exception:
            pass

        return None

    async def async_close(self) -> None:
        """Close the HTTP session."""
        if self.session:
            await self.session.close()
            self.session = None
