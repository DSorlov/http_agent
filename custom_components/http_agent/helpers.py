"""Helper utilities for HTTP Agent entities."""

from typing import Any

from homeassistant.config_entries import ConfigEntry

from .const import CONF_SENSOR_NAME, CONF_SENSORS, CONF_SENSOR_UNIT


def get_sensor_config(entry: ConfigEntry, sensor_name: str) -> dict[str, Any] | None:
    """Return sensor config by name from merged entry data and options."""
    data = dict(entry.data)
    if entry.options:
        data.update(entry.options)

    for config in data.get(CONF_SENSORS, []):
        if config.get(CONF_SENSOR_NAME) == sensor_name:
            # Ensure measurement unit is explicitly set to None if not provided to prevent casting to int by HA core
            if not config.get(CONF_SENSOR_UNIT):
                config[CONF_SENSOR_UNIT] = None

            return config

    return None
