"""HTTP Agent sensor platform."""
from __future__ import annotations

import asyncio
import logging
from datetime import timedelta
from typing import Any, Dict

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_NAME, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
)
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    CONF_SENSORS,
    CONF_SSL_VERIFY,
    CONF_TIMEOUT,
    CONF_INTERVAL,
    CONF_METHOD,
    CONF_PAYLOAD,
    CONF_QUERYSTRING,
    CONF_ENABLED,
    DEFAULT_TIMEOUT,
    DEFAULT_INTERVAL,
    DEFAULT_SSL_VERIFY,
    DEFAULT_METHOD,
    STATE_OK,
    STATE_ERROR,
    STATE_TIMEOUT,
    STATE_UNKNOWN,
)
from .coordinator import HTTPAgentCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HTTP Agent sensor based on a config entry."""
    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    
    sensors = []
    for sensor_config in config_entry.data.get(CONF_SENSORS, []):
        if sensor_config.get(CONF_ENABLED, True):
            sensor = HTTPAgentSensor(coordinator, sensor_config)
            sensors.append(sensor)
    
    if sensors:
        async_add_entities(sensors, True)


class HTTPAgentSensorCoordinator(DataUpdateCoordinator):
    """Individual coordinator for each sensor."""

    def __init__(
        self,
        hass: HomeAssistant,
        http_coordinator: HTTPAgentCoordinator,
        sensor_config: Dict[str, Any],
    ) -> None:
        """Initialize the sensor coordinator."""
        self.http_coordinator = http_coordinator
        self.sensor_config = sensor_config
        self._last_response = None
        
        update_interval = timedelta(seconds=sensor_config.get(CONF_INTERVAL, DEFAULT_INTERVAL))
        
        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_{sensor_config[CONF_NAME]}",
            update_interval=update_interval,
        )

    async def _async_update_data(self) -> Dict[str, Any]:
        """Fetch data from API endpoint."""
        if not self.sensor_config.get(CONF_ENABLED, True):
            return self._last_response or {"state": STATE_UNKNOWN}
        
        # Get template variables
        variables = {
            "states": self.hass.states,
            "now": dt_util.now(),
        }
        
        result = await self.http_coordinator.make_http_request(
            url=self.sensor_config[CONF_URL],
            method=self.sensor_config.get(CONF_METHOD, DEFAULT_METHOD),
            payload=self.sensor_config.get(CONF_PAYLOAD),
            timeout=self.sensor_config.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
            ssl_verify=self.sensor_config.get(CONF_SSL_VERIFY, DEFAULT_SSL_VERIFY),
            querystring=self.sensor_config.get(CONF_QUERYSTRING),
            variables=variables,
        )
        
        self._last_response = result
        return result


class HTTPAgentSensor(CoordinatorEntity, SensorEntity):
    """Representation of an HTTP Agent sensor."""

    def __init__(
        self,
        http_coordinator: HTTPAgentCoordinator,
        sensor_config: Dict[str, Any],
    ) -> None:
        """Initialize the sensor."""
        self.sensor_config = sensor_config
        self.http_coordinator = http_coordinator
        
        # Create individual coordinator for this sensor
        self.sensor_coordinator = HTTPAgentSensorCoordinator(
            http_coordinator.hass,
            http_coordinator,
            sensor_config,
        )
        
        super().__init__(self.sensor_coordinator)
        
        self._attr_name = sensor_config[CONF_NAME]
        self._attr_unique_id = f"{DOMAIN}_{sensor_config[CONF_NAME].lower().replace(' ', '_')}"
        self._attr_icon = "mdi:web"

    async def async_added_to_hass(self) -> None:
        """When entity is added to hass."""
        await super().async_added_to_hass()
        # Start the sensor coordinator
        await self.sensor_coordinator.async_config_entry_first_refresh()

    async def async_will_remove_from_hass(self) -> None:
        """When entity will be removed from hass."""
        # Stop the sensor coordinator
        if hasattr(self.sensor_coordinator, 'async_shutdown'):
            await self.sensor_coordinator.async_shutdown()
        await super().async_will_remove_from_hass()

    @property
    def icon(self) -> str:
        """Return the icon based on sensor status."""
        if not self.coordinator.data:
            return "mdi:web-off"
        
        state = self.coordinator.data.get("state")
        status_code = self.coordinator.data.get("status_code")
        
        # Icon based on state and status code
        if state == STATE_OK and status_code and 200 <= status_code < 300:
            return "mdi:web-check"
        elif state == STATE_TIMEOUT:
            return "mdi:web-clock"
        elif state == STATE_ERROR or (status_code and status_code >= 400):
            return "mdi:web-remove"
        elif not self.sensor_config.get(CONF_ENABLED, True):
            return "mdi:web-off"
        else:
            return "mdi:web"

    @property
    def state(self) -> str | None:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return STATE_UNKNOWN
        
        status_code = self.coordinator.data.get("status_code")
        if status_code is None:
            return self.coordinator.data.get("state", STATE_UNKNOWN)
        
        return str(status_code)

    @property
    def extra_state_attributes(self) -> Dict[str, Any] | None:
        """Return the state attributes."""
        if not self.coordinator.data:
            return None
        
        attributes = {
            "url": self.coordinator.data.get("url"),
            "method": self.coordinator.data.get("method"),
            "status_code": self.coordinator.data.get("status_code"),
            "state": self.coordinator.data.get("state"),
            "response": self.coordinator.data.get("response"),
            "response_text": self.coordinator.data.get("response_text"),
            "headers": self.coordinator.data.get("headers", {}),
            "last_updated": dt_util.now().isoformat(),
        }
        
        # Add error information if available
        if "error" in self.coordinator.data:
            attributes["error"] = self.coordinator.data["error"]
        
        # Add configuration details
        attributes.update({
            "interval": self.sensor_config.get(CONF_INTERVAL, DEFAULT_INTERVAL),
            "timeout": self.sensor_config.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
            "ssl_verify": self.sensor_config.get(CONF_SSL_VERIFY, DEFAULT_SSL_VERIFY),
            "enabled": self.sensor_config.get(CONF_ENABLED, True),
        })
        
        return attributes

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return (
            self.coordinator.last_update_success
            and self.sensor_config.get(CONF_ENABLED, True)
        )

    @property
    def device_info(self) -> Dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.http_coordinator.entry.entry_id)},
            "name": self.http_coordinator.entry.data.get(CONF_NAME, "HTTP Agent"),
            "manufacturer": "dsorlov",
            "model": "HTTP Agent",
            "sw_version": "1.0.0",
        }

    async def async_update(self) -> None:
        """Update the entity."""
        await self.sensor_coordinator.async_request_refresh()