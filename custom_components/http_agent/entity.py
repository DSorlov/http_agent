"""Shared entity base class for HTTP Agent."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from homeassistant.config_entries import ConfigSubentry
from homeassistant.const import CONF_ICON, CONF_METHOD, CONF_URL
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_ATTRIBUTES,
    CONF_VALUE_PATH,
    DEFAULT_METHOD,
    DOMAIN,
    MANUFACTURER,
)
from .coordinator import HTTPAgentConfigEntry, HTTPAgentCoordinator


class HTTPAgentEntity(CoordinatorEntity[HTTPAgentCoordinator]):
    """Base class for entities backed by a single value in the HTTP response."""

    _attr_has_entity_name = True
    _attr_name = None

    def __init__(
        self, coordinator: HTTPAgentCoordinator, subentry: ConfigSubentry
    ) -> None:
        """Initialise the entity from its config subentry."""
        super().__init__(coordinator)
        self.config: dict[str, Any] = dict(subentry.data)
        self._attr_unique_id = subentry.subentry_id
        self._attr_icon = self.config.get(CONF_ICON) or None
        # A device may only belong to one subentry, so each entity gets its own,
        # linked back to the endpoint device created in async_setup_entry.
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, subentry.subentry_id)},
            name=subentry.title,
            manufacturer=MANUFACTURER,
            model=subentry.subentry_type,
            entry_type=DeviceEntryType.SERVICE,
            via_device=(DOMAIN, coordinator.config_entry.entry_id),
        )

    @property
    def value(self) -> Any:
        """Return the raw value this entity is configured to read."""
        return self.coordinator.data.extract(self.config.get(CONF_VALUE_PATH))

    def path_value(self, key: str) -> Any:
        """Return the value for another configured path, e.g. latitude."""
        return self.coordinator.data.extract(self.config.get(key))

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return the extra attributes configured for this entity."""
        attributes = self.config.get(CONF_ATTRIBUTES) or {}
        if not attributes:
            return None
        return {
            name: self.coordinator.data.extract(path)
            for name, path in attributes.items()
        }


def hub_device_info(entry: HTTPAgentConfigEntry) -> DeviceInfo:
    """Return the device representing the endpoint itself."""
    url = entry.data.get(CONF_URL, "")
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=entry.title,
        manufacturer=MANUFACTURER,
        model=f"{entry.data.get(CONF_METHOD, DEFAULT_METHOD)} endpoint",
        configuration_url=url if url.startswith("http") and "{" not in url else None,
        entry_type=DeviceEntryType.SERVICE,
    )


def async_add_subentry_entities(
    entry: HTTPAgentConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
    subentry_type: str,
    factory: Callable[[HTTPAgentCoordinator, ConfigSubentry], Entity],
) -> None:
    """Create one entity per subentry of ``subentry_type``."""
    for subentry_id, subentry in entry.subentries.items():
        if subentry.subentry_type != subentry_type:
            continue
        async_add_entities(
            [factory(entry.runtime_data, subentry)], config_subentry_id=subentry_id
        )
