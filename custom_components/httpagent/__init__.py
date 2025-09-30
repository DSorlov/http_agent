"""HTTP Agent integration for Home Assistant."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.helpers.typing import ConfigType

from .const import DOMAIN
from .coordinator import HTTPAgentCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the HTTP Agent integration."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up HTTP Agent from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    
    coordinator = HTTPAgentCoordinator(hass, entry)
    hass.data[DOMAIN][entry.entry_id] = coordinator
    
    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    
    # Register services
    await _async_setup_services(hass, coordinator)
    
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[DOMAIN].pop(entry.entry_id)
    
    return unload_ok


async def _async_setup_services(hass: HomeAssistant, coordinator: HTTPAgentCoordinator) -> None:
    """Set up HTTP Agent services."""
    
    async def handle_http_request(call: ServiceCall) -> None:
        """Handle HTTP request service call."""
        await coordinator.handle_service_call(call)
    
    async def handle_http_get(call: ServiceCall) -> None:
        """Handle HTTP GET service call."""
        await coordinator.handle_service_call(call, method="GET")
    
    async def handle_http_post(call: ServiceCall) -> None:
        """Handle HTTP POST service call."""
        await coordinator.handle_service_call(call, method="POST")
    
    async def handle_http_put(call: ServiceCall) -> None:
        """Handle HTTP PUT service call."""
        await coordinator.handle_service_call(call, method="PUT")
    
    async def handle_http_delete(call: ServiceCall) -> None:
        """Handle HTTP DELETE service call."""
        await coordinator.handle_service_call(call, method="DELETE")
    
    # Register services
    hass.services.async_register(DOMAIN, "http_request", handle_http_request)
    hass.services.async_register(DOMAIN, "http_get", handle_http_get)
    hass.services.async_register(DOMAIN, "http_post", handle_http_post)
    hass.services.async_register(DOMAIN, "http_put", handle_http_put)
    hass.services.async_register(DOMAIN, "http_delete", handle_http_delete)