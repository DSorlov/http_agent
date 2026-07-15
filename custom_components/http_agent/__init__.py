"""HTTP Agent integration for Home Assistant."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import CONF_SENSOR_TYPE, CONF_SENSORS, DOMAIN
from .coordinator import HTTPAgentCoordinator
from .helpers import merge_entry_data

_LOGGER = logging.getLogger(__name__)

# Re-exported for convenience and backwards compatibility.
__all__ = ["DOMAIN", "async_setup_entry", "async_unload_entry"]

# ConfigEntry carrying the coordinator as typed runtime data.
HTTPAgentConfigEntry = ConfigEntry[HTTPAgentCoordinator]

PLATFORM_BY_SENSOR_TYPE: dict[str, Platform] = {
    "sensor": Platform.SENSOR,
    "binary_sensor": Platform.BINARY_SENSOR,
    "number": Platform.NUMBER,
    "device_tracker": Platform.DEVICE_TRACKER,
}


def _needed_platforms(data: dict) -> list[Platform]:
    """Return the platforms required for the configured sensors."""
    platforms: set[Platform] = set()
    for sensor_config in data.get(CONF_SENSORS, []):
        sensor_type = sensor_config.get(CONF_SENSOR_TYPE, "sensor")
        platform = PLATFORM_BY_SENSOR_TYPE.get(sensor_type)
        if platform is not None:
            platforms.add(platform)
    return list(platforms)


async def async_setup_entry(hass: HomeAssistant, entry: HTTPAgentConfigEntry) -> bool:
    """Set up HTTP Agent from a config entry."""
    data = merge_entry_data(entry)

    coordinator = HTTPAgentCoordinator(hass, data)

    # Fetch initial data
    await coordinator.async_config_entry_first_refresh()

    # Determine and remember which platforms are needed
    coordinator.platforms = _needed_platforms(data)
    entry.runtime_data = coordinator

    if coordinator.platforms:
        await hass.config_entries.async_forward_entry_setups(
            entry, coordinator.platforms
        )

    # Reload the entry when its options change
    entry.async_on_unload(entry.add_update_listener(async_update_options))

    return True


async def async_update_options(
    hass: HomeAssistant, entry: HTTPAgentConfigEntry
) -> None:
    """Reload the entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: HTTPAgentConfigEntry) -> bool:
    """Unload a config entry."""
    coordinator = entry.runtime_data

    unload_ok = True
    if coordinator.platforms:
        unload_ok = await hass.config_entries.async_unload_platforms(
            entry, coordinator.platforms
        )

    if unload_ok:
        # Clean up the coordinator's session
        await coordinator.async_close()

    return unload_ok
