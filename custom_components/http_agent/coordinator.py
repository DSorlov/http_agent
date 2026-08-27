"""Data update coordinator for HTTP Agent."""

from __future__ import annotations

from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_SCAN_INTERVAL
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import (
    CannotConnect,
    EmptyResponse,
    InvalidAuth,
    InvalidResponse,
    async_request,
)
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN
from .parser import ParsedResponse

_LOGGER = logging.getLogger(__name__)

type HTTPAgentConfigEntry = ConfigEntry[HTTPAgentCoordinator]


class HTTPAgentCoordinator(DataUpdateCoordinator[ParsedResponse]):
    """Fetch the configured endpoint once per interval and share the parsed body."""

    config_entry: HTTPAgentConfigEntry

    def __init__(self, hass: HomeAssistant, config_entry: HTTPAgentConfigEntry) -> None:
        """Initialise the coordinator from the config entry."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=config_entry,
            name=config_entry.title,
            update_interval=timedelta(
                seconds=config_entry.data.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
            ),
        )

    async def _async_update_data(self) -> ParsedResponse:
        """Fetch and parse the endpoint."""
        try:
            return await async_request(self.hass, dict(self.config_entry.data))
        except InvalidAuth as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN, translation_key="invalid_auth"
            ) from err
        except InvalidResponse as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="bad_status",
                translation_placeholders={"status": str(err.status)},
            ) from err
        except EmptyResponse as err:
            raise UpdateFailed(
                translation_domain=DOMAIN, translation_key="empty_response"
            ) from err
        except CannotConnect as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="cannot_connect",
                translation_placeholders={"error": str(err)},
            ) from err
