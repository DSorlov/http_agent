"""Binary sensor platform for HTTP Agent."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import CONF_DEVICE_CLASS
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    CONF_PAYLOAD_OFF,
    CONF_PAYLOAD_ON,
    FALSY_VALUES,
    SUBENTRY_TYPE_BINARY_SENSOR,
    TRUTHY_VALUES,
)
from .coordinator import HTTPAgentConfigEntry
from .entity import HTTPAgentEntity, async_add_subentry_entities

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HTTPAgentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the HTTP Agent binary sensors."""
    async_add_subentry_entities(
        entry, async_add_entities, SUBENTRY_TYPE_BINARY_SENSOR, HTTPAgentBinarySensor
    )


class HTTPAgentBinarySensor(HTTPAgentEntity, BinarySensorEntity):
    """A binary sensor reading a single value from the HTTP response."""

    def __init__(self, coordinator, subentry) -> None:
        """Initialise the binary sensor from its subentry configuration."""
        super().__init__(coordinator, subentry)
        device_class = self.config.get(CONF_DEVICE_CLASS)
        try:
            self._attr_device_class = (
                BinarySensorDeviceClass(device_class) if device_class else None
            )
        except ValueError:
            _LOGGER.warning("Ignoring unsupported device class '%s'", device_class)
            self._attr_device_class = None

    @property
    def is_on(self) -> bool | None:
        """Return whether the extracted value represents an "on" state."""
        return _as_bool(
            self.value,
            self.config.get(CONF_PAYLOAD_ON),
            self.config.get(CONF_PAYLOAD_OFF),
        )


def _as_bool(
    value: Any, payload_on: str | None, payload_off: str | None
) -> bool | None:
    """Interpret ``value`` as a boolean, honouring explicit on/off payloads."""
    if value is None:
        return None

    text = str(value).strip()
    if payload_on and text == payload_on:
        return True
    if payload_off and text == payload_off:
        return False
    if payload_on and payload_off:
        return None
    if payload_on:
        return False
    if payload_off:
        return True

    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value != 0

    lowered = text.lower()
    if lowered in TRUTHY_VALUES:
        return True
    if lowered in FALSY_VALUES:
        return False
    if not lowered:
        return False

    _LOGGER.debug("Value %r could not be interpreted as a boolean", value)
    return None
