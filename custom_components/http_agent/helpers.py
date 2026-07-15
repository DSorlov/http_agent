"""Helper utilities for HTTP Agent entities."""

from __future__ import annotations

from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.device_registry import DeviceInfo

from .const import (
    CONF_SENSOR_DEVICE_CLASS,
    CONF_SENSOR_NAME,
    CONF_SENSOR_UNIT,
    CONF_SENSORS,
    DOMAIN,
)


def merge_entry_data(entry: ConfigEntry) -> dict[str, Any]:
    """Return config entry data merged with any options."""
    data = dict(entry.data)
    if entry.options:
        data.update(entry.options)
    return data


def get_sensor_config(entry: ConfigEntry, sensor_name: str) -> dict[str, Any] | None:
    """Return sensor config by name from merged entry data and options."""
    data = merge_entry_data(entry)

    for config in data.get(CONF_SENSORS, []):
        if config.get(CONF_SENSOR_NAME) == sensor_name:
            # Ensure measurement unit is explicitly set to None if not provided to
            # prevent casting to int by HA core.
            if not config.get(CONF_SENSOR_UNIT):
                config[CONF_SENSOR_UNIT] = None

            return config

    return None


def normalize_device_class(value: Any) -> str | None:
    """Normalize a stored device class value, treating sentinels as no class."""
    if value in (None, "", "none"):
        return None
    return value


def get_device_class(sensor_config: dict[str, Any] | None) -> str | None:
    """Return the normalized device class for a sensor config."""
    if not sensor_config:
        return None
    return normalize_device_class(sensor_config.get(CONF_SENSOR_DEVICE_CLASS))


def build_device_info(entry: ConfigEntry) -> DeviceInfo:
    """Return shared device information for all entities of a config entry."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer="HTTP Agent",
        model="HTTP Agent",
    )
