"""HTTP Agent sensor platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.sensor import SensorEntity
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
from .helpers import get_sensor_config

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up HTTP Agent sensors from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    # Merge config data with options
    data = dict(entry.data)
    if entry.options:
        data.update(entry.options)

    sensors = []
    for sensor_config in data[CONF_SENSORS]:
        # Only create sensors of type "sensor"
        if sensor_config.get(CONF_SENSOR_TYPE, "sensor") == "sensor":
            sensor_name = sensor_config[CONF_SENSOR_NAME]
            sensors.append(HTTPAgentSensor(coordinator, entry, sensor_name))

    async_add_entities(sensors)

    # Clean up removed sensors from entity registry
    from homeassistant.helpers import entity_registry as er

    entity_registry = er.async_get(hass)

    # Get current sensor names
    current_sensor_names = {
        sensor_config[CONF_SENSOR_NAME] for sensor_config in data[CONF_SENSORS]
    }

    # Find entities to remove (create list first to avoid iteration error)
    entities_to_remove = []
    for entity_id, entity_entry in entity_registry.entities.items():
        if (
            entity_entry.config_entry_id == entry.entry_id
            and entity_entry.domain == "sensor"
            and entity_entry.platform == DOMAIN
        ):

            # Extract sensor name from unique_id
            unique_id = entity_entry.unique_id
            if unique_id and "_" in unique_id:
                sensor_name = unique_id.split("_", 1)[1]
                if sensor_name not in current_sensor_names:
                    entities_to_remove.append(entity_id)

    # Remove obsolete entities
    for entity_id in entities_to_remove:
        _LOGGER.info("Removing obsolete sensor entity: %s", entity_id)
        entity_registry.async_remove(entity_id)


class HTTPAgentSensor(CoordinatorEntity, SensorEntity):
    """HTTP Agent sensor."""

    def __init__(
        self,
        coordinator: HTTPAgentCoordinator,
        entry: ConfigEntry,
        sensor_name: str,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entry = entry
        self.sensor_name = sensor_name

        # Entity properties
        self._attr_name = sensor_name
        self._attr_unique_id = f"{entry.entry_id}_{sensor_name}"

        self.sensor_config = get_sensor_config(entry, sensor_name)

    @property
    def name(self) -> str:
        """Return the name of the sensor."""
        return self.sensor_name

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if not self.coordinator.data:
            return None

        sensor_data = self.coordinator.data.get(self.sensor_name, {})
        return sensor_data.get("state")

    @property
    def device_class(self) -> str | None:
        """Return the device class of the sensor."""
        if self.sensor_config:
            return self.sensor_config.get(CONF_SENSOR_DEVICE_CLASS)
        return None

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the unit of measurement of the sensor."""
        if self.sensor_config:
            return self.sensor_config.get(CONF_SENSOR_UNIT)
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
            "model": "HTTP Sensor",
            "sw_version": "1.0.0",
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success
