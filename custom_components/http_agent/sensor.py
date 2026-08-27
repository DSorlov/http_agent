"""Sensor platform for HTTP Agent."""

from __future__ import annotations

from datetime import date, datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import CONF_DEVICE_CLASS, CONF_UNIT_OF_MEASUREMENT
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import CONF_STATE_CLASS, SUBENTRY_TYPE_SENSOR
from .coordinator import HTTPAgentConfigEntry
from .entity import HTTPAgentEntity, async_add_subentry_entities

_LOGGER = logging.getLogger(__name__)

_NUMERIC_STATE_CLASSES = {
    SensorStateClass.MEASUREMENT,
    SensorStateClass.TOTAL,
    SensorStateClass.TOTAL_INCREASING,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HTTPAgentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the HTTP Agent sensors."""
    async_add_subentry_entities(
        entry, async_add_entities, SUBENTRY_TYPE_SENSOR, HTTPAgentSensor
    )


class HTTPAgentSensor(HTTPAgentEntity, SensorEntity):
    """A sensor reading a single value from the HTTP response."""

    def __init__(self, coordinator, subentry) -> None:
        """Initialise the sensor from its subentry configuration."""
        super().__init__(coordinator, subentry)
        self._attr_device_class = _enum_or_none(
            SensorDeviceClass, self.config.get(CONF_DEVICE_CLASS)
        )
        self._attr_state_class = _enum_or_none(
            SensorStateClass, self.config.get(CONF_STATE_CLASS)
        )
        self._attr_native_unit_of_measurement = (
            self.config.get(CONF_UNIT_OF_MEASUREMENT) or None
        )

    @property
    def native_value(self) -> str | float | date | datetime | None:
        """Return the extracted value, coerced to match the device class."""
        value = self.value
        if value is None:
            return None

        if self._attr_device_class in (
            SensorDeviceClass.TIMESTAMP,
            SensorDeviceClass.DATE,
        ):
            return _as_datetime(value, self._attr_device_class)

        if (
            self._attr_state_class in _NUMERIC_STATE_CLASSES
            or self._attr_native_unit_of_measurement
        ):
            return _as_float(value)

        return str(value)


def _enum_or_none(enum_cls: Any, value: Any) -> Any:
    """Return ``value`` as a member of ``enum_cls``, or None when unsupported."""
    if not value:
        return None
    try:
        return enum_cls(value)
    except ValueError:
        _LOGGER.warning("Ignoring unsupported %s '%s'", enum_cls.__name__, value)
        return None


def _as_float(value: Any) -> float | None:
    """Return ``value`` as a float, or None when it is not numeric."""
    if isinstance(value, bool):
        return float(value)
    try:
        return float(str(value).strip().replace(",", "."))
    except (TypeError, ValueError):
        _LOGGER.debug("Value %r is not numeric", value)
        return None


def _as_datetime(value: Any, device_class: SensorDeviceClass) -> date | datetime | None:
    """Return ``value`` parsed as a timestamp or date."""
    if device_class is SensorDeviceClass.DATE:
        return dt_util.parse_date(str(value))
    if (parsed := dt_util.parse_datetime(str(value))) is not None:
        return dt_util.as_utc(parsed) if parsed.tzinfo is None else parsed
    if (number := _as_float(value)) is not None:
        return dt_util.utc_from_timestamp(number)
    return None
