"""Device tracker platform for HTTP Agent."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.device_tracker import SourceType, TrackerEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_GPS_ACCURACY_PATH,
    CONF_LATITUDE_PATH,
    CONF_LONGITUDE_PATH,
    CONF_SOURCE_TYPE,
    SUBENTRY_TYPE_DEVICE_TRACKER,
)
from .coordinator import HTTPAgentConfigEntry
from .entity import HTTPAgentEntity, async_add_subentry_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HTTPAgentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the HTTP Agent device trackers."""
    async_add_subentry_entities(
        entry, async_add_entities, SUBENTRY_TYPE_DEVICE_TRACKER, HTTPAgentDeviceTracker
    )


class HTTPAgentDeviceTracker(HTTPAgentEntity, TrackerEntity):
    """A device tracker reading coordinates from the HTTP response."""

    def __init__(self, coordinator, subentry) -> None:
        """Initialise the tracker from its subentry configuration."""
        super().__init__(coordinator, subentry)
        try:
            self._source_type = SourceType(self.config.get(CONF_SOURCE_TYPE, "gps"))
        except ValueError:
            self._source_type = SourceType.GPS

    @property
    def source_type(self) -> SourceType:
        """Return the configured source type."""
        return self._source_type

    @property
    def latitude(self) -> float | None:
        """Return the current latitude."""
        return _as_float(self.path_value(CONF_LATITUDE_PATH))

    @property
    def longitude(self) -> float | None:
        """Return the current longitude."""
        return _as_float(self.path_value(CONF_LONGITUDE_PATH))

    @property
    def location_accuracy(self) -> int:
        """Return the GPS accuracy in meters."""
        accuracy = _as_float(self.path_value(CONF_GPS_ACCURACY_PATH))
        return int(accuracy) if accuracy is not None else 0


def _as_float(value: Any) -> float | None:
    """Return ``value`` as a float, or None when it is not numeric."""
    if value is None:
        return None
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        _LOGGER.debug("Value %r is not a valid coordinate", value)
        return None
