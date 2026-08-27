"""Diagnostics support for HTTP Agent."""

from __future__ import annotations

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.const import (
    CONF_API_KEY,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_URL,
    CONF_USERNAME,
)
from homeassistant.core import HomeAssistant

from .api import build_request_headers, redact_headers
from .const import MAX_PREVIEW_LENGTH
from .coordinator import HTTPAgentConfigEntry

TO_REDACT = {
    CONF_API_KEY,
    CONF_PASSWORD,
    CONF_TOKEN,
    CONF_URL,
    CONF_USERNAME,
    "headers",
}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: HTTPAgentConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry, with credentials removed."""
    coordinator = entry.runtime_data
    response = coordinator.data

    return {
        "entry": async_redact_data(dict(entry.data), TO_REDACT),
        "request_headers": redact_headers(build_request_headers(dict(entry.data))),
        "subentries": [
            {
                "type": subentry.subentry_type,
                "title": subentry.title,
                "data": dict(subentry.data),
            }
            for subentry in entry.subentries.values()
        ],
        "response": {
            "status": response.status if response else None,
            "format": response.format if response else None,
            "headers": redact_headers(response.headers) if response else None,
            "body": response.text[:MAX_PREVIEW_LENGTH] if response else None,
        },
        "last_update_success": coordinator.last_update_success,
    }
