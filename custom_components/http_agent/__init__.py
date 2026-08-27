"""The HTTP Agent integration."""

from __future__ import annotations

import logging
from types import MappingProxyType
from typing import Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import (
    CONF_DEVICE_CLASS,
    CONF_HEADERS,
    CONF_ICON,
    CONF_METHOD,
    CONF_NAME,
    CONF_PAYLOAD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_URL,
    CONF_VERIFY_SSL,
    Platform,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, device_registry as dr
from homeassistant.helpers.typing import ConfigType

from .const import (
    AUTH_NONE,
    CONF_ATTRIBUTES,
    CONF_AUTH_TYPE,
    CONF_CONTENT_TYPE,
    CONF_FOLLOW_REDIRECTS,
    CONF_LATITUDE_PATH,
    CONF_LONGITUDE_PATH,
    CONF_RESPONSE_FORMAT,
    CONF_RETRIES,
    CONF_SOURCE_TYPE,
    CONF_VALUE_PATH,
    CONFIG_VERSION,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_FOLLOW_REDIRECTS,
    DEFAULT_METHOD,
    DEFAULT_RETRIES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    FORMAT_AUTO,
    SUBENTRY_TYPE_BINARY_SENSOR,
    SUBENTRY_TYPE_DEVICE_TRACKER,
    SUBENTRY_TYPE_SENSOR,
)
from .coordinator import HTTPAgentConfigEntry, HTTPAgentCoordinator
from .entity import hub_device_info
from .services import async_setup_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.BINARY_SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.SENSOR,
]

# Legacy (version 1) keys, only referenced by the migration below.
_LEGACY_SENSORS = "sensors"
_LEGACY_INTERVAL = "interval"
_LEGACY_MAP = {
    "sensor_state": CONF_VALUE_PATH,
    "sensor_icon": CONF_ICON,
    "sensor_device_class": CONF_DEVICE_CLASS,
    "sensor_unit": CONF_UNIT_OF_MEASUREMENT,
    "tracker_latitude": CONF_LATITUDE_PATH,
    "tracker_longitude": CONF_LONGITUDE_PATH,
    "tracker_source_type": CONF_SOURCE_TYPE,
}
_LEGACY_TYPES = {
    "sensor": SUBENTRY_TYPE_SENSOR,
    "number": SUBENTRY_TYPE_SENSOR,
    "binary_sensor": SUBENTRY_TYPE_BINARY_SENSOR,
    "device_tracker": SUBENTRY_TYPE_DEVICE_TRACKER,
}

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register the integration actions."""
    async_setup_services(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: HTTPAgentConfigEntry) -> bool:
    """Set up HTTP Agent from a config entry."""
    coordinator = HTTPAgentCoordinator(hass, entry)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator

    dr.async_get(hass).async_get_or_create(
        config_entry_id=entry.entry_id, **hub_device_info(entry)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    entry.async_on_unload(entry.add_update_listener(_async_reload_entry))
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HTTPAgentConfigEntry) -> bool:
    """Unload a config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_reload_entry(hass: HomeAssistant, entry: HTTPAgentConfigEntry) -> None:
    """Reload the entry when its configuration or subentries change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_migrate_entry(hass: HomeAssistant, entry: HTTPAgentConfigEntry) -> bool:
    """Migrate a version 1 entry to the subentry based version 2 layout."""
    if entry.version > CONFIG_VERSION:
        return False
    if entry.version == CONFIG_VERSION:
        return True

    _LOGGER.debug("Migrating HTTP Agent entry %s from version 1", entry.entry_id)

    legacy: dict[str, Any] = {**entry.data, **entry.options}

    headers = {
        header["key"]: header["value"]
        for header in legacy.get(CONF_HEADERS) or []
        if isinstance(header, dict) and header.get("key")
    }

    data = {
        CONF_URL: legacy.get(CONF_URL, ""),
        CONF_METHOD: legacy.get(CONF_METHOD, DEFAULT_METHOD),
        CONF_AUTH_TYPE: AUTH_NONE,
        CONF_HEADERS: headers,
        CONF_PAYLOAD: legacy.get(CONF_PAYLOAD, ""),
        CONF_CONTENT_TYPE: legacy.get(CONF_CONTENT_TYPE, DEFAULT_CONTENT_TYPE),
        CONF_RESPONSE_FORMAT: FORMAT_AUTO,
        CONF_SCAN_INTERVAL: legacy.get(_LEGACY_INTERVAL, DEFAULT_SCAN_INTERVAL),
        CONF_TIMEOUT: legacy.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
        CONF_RETRIES: legacy.get(CONF_RETRIES, DEFAULT_RETRIES),
        CONF_VERIFY_SSL: legacy.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
        CONF_FOLLOW_REDIRECTS: DEFAULT_FOLLOW_REDIRECTS,
    }

    subentries = [
        _migrate_sensor(sensor) for sensor in legacy.get(_LEGACY_SENSORS) or []
    ]

    hass.config_entries.async_update_entry(
        entry,
        data=data,
        options={},
        version=CONFIG_VERSION,
        minor_version=1,
    )
    for subentry in subentries:
        hass.config_entries.async_add_subentry(entry, subentry)
    return True


def _migrate_sensor(sensor: dict[str, Any]) -> ConfigSubentry:
    """Convert one legacy sensor definition into a config subentry."""
    name = sensor.get("sensor_name") or "Sensor"
    data: dict[str, Any] = {CONF_NAME: name}

    for legacy_key, new_key in _LEGACY_MAP.items():
        value = sensor.get(legacy_key)
        if value in (None, "", "none"):
            continue
        data[new_key] = value

    if color_path := sensor.get("sensor_color"):
        data[CONF_ATTRIBUTES] = {"color": color_path}

    return ConfigSubentry(
        data=MappingProxyType(data),
        subentry_type=_LEGACY_TYPES.get(
            sensor.get("sensor_type", "sensor"), SUBENTRY_TYPE_SENSOR
        ),
        title=name,
        unique_id=None,
    )
