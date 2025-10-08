"""HTTP Agent device tracker platform."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import TrackerEntity
from homeassistant.components.device_tracker.const import SourceType
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
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
    """Set up HTTP Agent device trackers from a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    # Merge config data with options
    data = dict(entry.data)
    if entry.options:
        data.update(entry.options)

    trackers = []
    for sensor_config in data[CONF_SENSORS]:
        # Only create device trackers of type "device_tracker"
        if sensor_config.get(CONF_SENSOR_TYPE, "sensor") == "device_tracker":
            sensor_name = sensor_config[CONF_SENSOR_NAME]
            trackers.append(HTTPAgentDeviceTracker(coordinator, entry, sensor_name))

    if trackers:
        async_add_entities(trackers)


class HTTPAgentDeviceTracker(CoordinatorEntity, TrackerEntity):
    """HTTP Agent device tracker."""

    def __init__(
        self,
        coordinator: HTTPAgentCoordinator,
        entry: ConfigEntry,
        sensor_name: str,
    ) -> None:
        """Initialize the device tracker."""
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
        """Return the name of the device tracker."""
        return self.sensor_name

    @property
    def latitude(self) -> float | None:
        """Return latitude value of the device."""
        if not self.coordinator.data:
            return None

        sensor_data = self.coordinator.data.get(self.sensor_name, {})
        lat = sensor_data.get("latitude")

        if lat is not None:
            try:
                return float(lat)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Could not convert latitude '%s' to float for %s",
                    lat,
                    self.sensor_name,
                )
        return None

    @property
    def longitude(self) -> float | None:
        """Return longitude value of the device."""
        if not self.coordinator.data:
            return None

        sensor_data = self.coordinator.data.get(self.sensor_name, {})
        lng = sensor_data.get("longitude")

        if lng is not None:
            try:
                return float(lng)
            except (ValueError, TypeError):
                _LOGGER.warning(
                    "Could not convert longitude '%s' to float for %s",
                    lng,
                    self.sensor_name,
                )
        return None

    @property
    def location_name(self) -> str | None:
        """Return a location name for the current location of the device."""
        if not self.coordinator.data:
            return None

        sensor_data = self.coordinator.data.get(self.sensor_name, {})
        location = sensor_data.get("location_name")

        # Fallback to state if no location_name is provided
        if not location:
            location = sensor_data.get("state")

        return str(location) if location is not None else None

    @property
    def source_type(self) -> SourceType:
        """Return the source type, eg gps or router, of the device."""
        if not self.coordinator.data:
            return SourceType.GPS

        sensor_data = self.coordinator.data.get(self.sensor_name, {})
        source = sensor_data.get("source_type", "gps")

        # Convert string to SourceType
        if source.lower() == "router":
            return SourceType.ROUTER
        elif source.lower() == "bluetooth":
            return SourceType.BLUETOOTH
        elif source.lower() == "bluetooth_le":
            return SourceType.BLUETOOTH_LE
        else:
            return SourceType.GPS

    @property
    def icon(self) -> str | None:
        """Return the icon of the device tracker."""
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
        """Return the state attributes of the device tracker."""
        if not self.coordinator.data:
            return {}

        sensor_data = self.coordinator.data.get(self.sensor_name, {})
        attributes = {}

        # Add color if available
        if sensor_data.get("color"):
            attributes["color"] = sensor_data["color"]

        # Add raw coordinates for debugging
        if sensor_data.get("latitude") is not None:
            attributes["raw_latitude"] = sensor_data["latitude"]
        if sensor_data.get("longitude") is not None:
            attributes["raw_longitude"] = sensor_data["longitude"]

        return attributes

    @property
    def device_info(self) -> dict[str, Any]:
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self.entry.entry_id)},
            "name": self.entry.title,
            "manufacturer": "HTTP Agent",
            "model": "HTTP Device Tracker",
            "sw_version": "1.0.0",
        }

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self.coordinator.last_update_success
