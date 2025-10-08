"""HTTP Agent binary sensor platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_SENSOR_DEVICE_CLASS,
    CONF_SENSOR_NAME,
    CONF_SENSOR_TYPE,
    CONF_SENSORS,
    DOMAIN,
)
from .coordinator import HTTPAgentCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HTTP Agent binary sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Merge config data with options
    data = dict(entry.data)
    if entry.options:
        data.update(entry.options)

    sensors = []
    for sensor_config in data[CONF_SENSORS]:
        # Only create binary sensors of type "binary_sensor"
        if sensor_config.get(CONF_SENSOR_TYPE, "sensor") == "binary_sensor":
            sensor_name = sensor_config[CONF_SENSOR_NAME]
            sensors.append(HTTPAgentBinarySensor(coordinator, entry, sensor_name))

    if sensors:
        async_add_entities(sensors)


class HTTPAgentBinarySensor(CoordinatorEntity, BinarySensorEntity):
    """HTTP Agent binary sensor."""

    def __init__(
        self,
        coordinator: HTTPAgentCoordinator,
        entry: ConfigEntry,
        sensor_name: str,
    ) -> None:
        """Initialize the binary sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.sensor_name = sensor_name

        # Entity properties
        self._attr_name = sensor_name
        self._attr_unique_id = f"{entry.entry_id}_{sensor_name}"

        # Find sensor config
        self.sensor_config = None
        data = dict(entry.data)
        if entry.options:
            data.update(entry.options)

        for config in data[CONF_SENSORS]:
            if config[CONF_SENSOR_NAME] == sensor_name:
                self.sensor_config = config
                break

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self.sensor_name

    @property
    def is_on(self) -> bool | None:
        """Return true if the binary sensor is on."""
        if not self.coordinator.data:
            return None

        sensor_data = self.coordinator.data.get(self.sensor_name, {})
        state = sensor_data.get("state")

        # Convert state to boolean
        if state is None:
            return None

        if isinstance(state, bool):
            return state

        if isinstance(state, str):
            return state.lower() in ("true", "on", "yes", "1", "active", "open")

        if isinstance(state, (int, float)):
            return state > 0

        return bool(state)

    @property
    def device_class(self) -> str | None:
        """Return the device class of the binary sensor."""
        if self.sensor_config:
            return self.sensor_config.get(CONF_SENSOR_DEVICE_CLASS)
        return None

    @property
    def icon(self) -> str | None:
        """Return the icon of the sensor."""
        if not self.coordinator.data:
            return None

        sensor_data = self.coordinator.data.get(self.sensor_name, {})
        icon = sensor_data.get("icon")

        # If icon is provided, ensure it starts with mdi:
        if icon and not icon.startswith("mdi:"):
            icon = f"mdi:{icon}"

        return icon

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the state attributes of the sensor."""
        if not self.coordinator.data:
            return {}

        sensor_data = self.coordinator.data.get(self.sensor_name, {})
        attributes = {}

        # Add color if available
        if sensor_data.get("color"):
            attributes["color"] = sensor_data["color"]

        return attributes

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": self.entry.title,
            "manufacturer": "HTTP Agent",
            "model": "HTTP Binary Sensor",
            "sw_version": "1.0.0",
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success
