"""HTTP Agent number platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.number import NumberEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_SENSOR_DEVICE_CLASS,
    CONF_SENSOR_NAME,
    CONF_SENSOR_TYPE,
    CONF_SENSOR_UNIT,
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
    """Set up HTTP Agent number entities from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Merge config data with options
    data = dict(entry.data)
    if entry.options:
        data.update(entry.options)

    numbers = []
    for sensor_config in data[CONF_SENSORS]:
        # Only create numbers of type "number"
        if sensor_config.get(CONF_SENSOR_TYPE, "sensor") == "number":
            sensor_name = sensor_config[CONF_SENSOR_NAME]
            numbers.append(HTTPAgentNumber(coordinator, entry, sensor_name))

    if numbers:
        async_add_entities(numbers)


class HTTPAgentNumber(CoordinatorEntity, NumberEntity):
    """HTTP Agent number entity."""

    def __init__(
        self,
        coordinator: HTTPAgentCoordinator,
        entry: ConfigEntry,
        sensor_name: str,
    ) -> None:
        """Initialize the number entity."""
        super().__init__(coordinator)
        self.entry = entry
        self.sensor_name = sensor_name

        # Entity properties
        self._attr_name = sensor_name
        self._attr_unique_id = f"{entry.entry_id}_{sensor_name}"

        # Number entities are read-only for HTTP Agent
        self._attr_mode = "box"

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
        """Return the name of the number entity."""
        return self.sensor_name

    @property
    def native_value(self) -> float | None:
        """Return the value of the number entity."""
        if not self.coordinator.data:
            return None

        sensor_data = self.coordinator.data.get(self.sensor_name, {})
        state = sensor_data.get("state")

        # Convert state to float
        if state is None:
            return None

        try:
            return float(state)
        except (ValueError, TypeError):
            _LOGGER.warning(
                "Could not convert state '%s' to number for %s", state, self.sensor_name
            )
            return None

    @property
    def device_class(self) -> str | None:
        """Return the device class of the number entity."""
        if self.sensor_config:
            return self.sensor_config.get(CONF_SENSOR_DEVICE_CLASS)
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of the number entity."""
        if self.sensor_config:
            return self.sensor_config.get(CONF_SENSOR_UNIT)
        return None

    @property
    def icon(self) -> str | None:
        """Return the icon of the number entity."""
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
        """Return the state attributes of the number entity."""
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
            "model": "HTTP Number",
            "sw_version": "1.0.0",
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success

    # Number entities from HTTP Agent are read-only
    async def async_set_native_value(self, value: float) -> None:
        """Set new value - not supported for HTTP Agent."""
        raise NotImplementedError("HTTP Agent numbers are read-only")
