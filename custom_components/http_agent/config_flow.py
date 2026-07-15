"""Config flow for HTTP Agent integration."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    BooleanSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TemplateSelector,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .const import (
    BINARY_SENSOR_DEVICE_CLASSES,
    CONF_CONTENT_TYPE,
    CONF_HEADERS,
    CONF_INTERVAL,
    CONF_METHOD,
    CONF_PAYLOAD,
    CONF_RETRIES,
    CONF_SENSOR_COLOR,
    CONF_SENSOR_DEVICE_CLASS,
    CONF_SENSOR_ICON,
    CONF_SENSOR_NAME,
    CONF_SENSOR_STATE,
    CONF_SENSOR_TYPE,
    CONF_SENSOR_UNIT,
    CONF_SENSORS,
    CONF_TIMEOUT,
    CONF_TRACKER_LATITUDE,
    CONF_TRACKER_LOCATION_NAME,
    CONF_TRACKER_LONGITUDE,
    CONF_TRACKER_SOURCE_TYPE,
    CONF_URL,
    CONF_VERIFY_SSL,
    CONTENT_TYPES,
    DEFAULT_INTERVAL,
    DEFAULT_METHOD,
    DEFAULT_RETRIES,
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    HTTP_METHODS,
    HTTP_METHODS_WITH_PAYLOAD,
    NUMBER_DEVICE_CLASSES,
    SENSOR_DEVICE_CLASSES,
    SENSOR_TYPES,
)

_LOGGER = logging.getLogger(__name__)

SOURCE_TYPES = ["none", "gps", "router", "bluetooth", "bluetooth_le"]

# Optional sensor fields that should always be present on a stored sensor config
_OPTIONAL_SENSOR_FIELDS = (
    CONF_SENSOR_STATE,
    CONF_SENSOR_ICON,
    CONF_SENSOR_COLOR,
    CONF_SENSOR_DEVICE_CLASS,
    CONF_SENSOR_UNIT,
    CONF_TRACKER_LATITUDE,
    CONF_TRACKER_LONGITUDE,
    CONF_TRACKER_LOCATION_NAME,
    CONF_TRACKER_SOURCE_TYPE,
)


# ---------------------------------------------------------------------------
# Schema builders (shared between config and options flows)
# ---------------------------------------------------------------------------
def _basic_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return the schema for the basic connection settings."""
    return vol.Schema(
        {
            vol.Required(CONF_URL, default=defaults.get(CONF_URL, "")): TextSelector(
                TextSelectorConfig(type=TextSelectorType.URL)
            ),
            vol.Required(
                CONF_METHOD, default=defaults.get(CONF_METHOD, DEFAULT_METHOD)
            ): SelectSelector(
                SelectSelectorConfig(
                    options=HTTP_METHODS, mode=SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Optional(
                CONF_TIMEOUT, default=defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=1,
                    max=300,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Required(
                CONF_RETRIES, default=defaults.get(CONF_RETRIES, DEFAULT_RETRIES)
            ): NumberSelector(
                NumberSelectorConfig(min=0, max=10, step=1, mode=NumberSelectorMode.BOX)
            ),
            vol.Optional(
                CONF_INTERVAL, default=defaults.get(CONF_INTERVAL, DEFAULT_INTERVAL)
            ): NumberSelector(
                NumberSelectorConfig(
                    min=5,
                    max=86400,
                    step=1,
                    mode=NumberSelectorMode.BOX,
                    unit_of_measurement="s",
                )
            ),
            vol.Optional(
                CONF_VERIFY_SSL,
                default=defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            ): BooleanSelector(),
        }
    )


def _payload_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Return the schema for the request payload settings."""
    return vol.Schema(
        {
            vol.Required(
                CONF_CONTENT_TYPE,
                default=defaults.get(CONF_CONTENT_TYPE, "application/json"),
            ): SelectSelector(
                SelectSelectorConfig(
                    options=CONTENT_TYPES, mode=SelectSelectorMode.DROPDOWN
                )
            ),
            vol.Optional(
                CONF_PAYLOAD, default=defaults.get(CONF_PAYLOAD, "")
            ): TemplateSelector(),
        }
    )


def _header_schema() -> vol.Schema:
    """Return the schema for adding a header."""
    return vol.Schema(
        {
            vol.Required("key"): TextSelector(),
            vol.Required("value"): TextSelector(),
        }
    )


def _add_sensor_schema(defaults: dict[str, Any] | None = None) -> vol.Schema:
    """Return the schema for choosing a sensor name and type."""
    defaults = defaults or {}
    return vol.Schema(
        {
            vol.Required(
                CONF_SENSOR_NAME, default=defaults.get(CONF_SENSOR_NAME, "")
            ): TextSelector(),
            vol.Required(
                CONF_SENSOR_TYPE, default=defaults.get(CONF_SENSOR_TYPE, "sensor")
            ): SelectSelector(
                SelectSelectorConfig(
                    options=list(SENSOR_TYPES.keys()),
                    mode=SelectSelectorMode.DROPDOWN,
                    translation_key="sensor_type",
                )
            ),
        }
    )


def _device_class_selector(classes: set[str]) -> SelectSelector:
    """Return a dropdown selector for a device class, including a 'none' option."""
    return SelectSelector(
        SelectSelectorConfig(
            options=["none", *sorted(classes)],
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _sensor_config_schema(
    sensor_type: str,
    sensor: dict[str, Any] | None = None,
    include_name: bool = False,
) -> vol.Schema:
    """Return the configuration schema for a specific sensor type."""
    sensor = sensor or {}
    schema: dict[Any, Any] = {}

    if include_name:
        schema[
            vol.Required(CONF_SENSOR_NAME, default=sensor.get(CONF_SENSOR_NAME, ""))
        ] = TextSelector()

    schema[
        vol.Required(CONF_SENSOR_STATE, default=sensor.get(CONF_SENSOR_STATE, ""))
    ] = TextSelector()
    schema[vol.Optional(CONF_SENSOR_ICON, default=sensor.get(CONF_SENSOR_ICON, ""))] = (
        TextSelector()
    )
    schema[
        vol.Optional(CONF_SENSOR_COLOR, default=sensor.get(CONF_SENSOR_COLOR, ""))
    ] = TextSelector()

    if sensor_type in ("sensor", "number"):
        classes = (
            SENSOR_DEVICE_CLASSES if sensor_type == "sensor" else NUMBER_DEVICE_CLASSES
        )
        schema[
            vol.Optional(
                CONF_SENSOR_DEVICE_CLASS,
                default=sensor.get(CONF_SENSOR_DEVICE_CLASS) or "none",
            )
        ] = _device_class_selector(classes)
        schema[
            vol.Optional(CONF_SENSOR_UNIT, default=sensor.get(CONF_SENSOR_UNIT) or "")
        ] = TextSelector()
    elif sensor_type == "binary_sensor":
        schema[
            vol.Optional(
                CONF_SENSOR_DEVICE_CLASS,
                default=sensor.get(CONF_SENSOR_DEVICE_CLASS) or "none",
            )
        ] = _device_class_selector(BINARY_SENSOR_DEVICE_CLASSES)
    elif sensor_type == "device_tracker":
        schema[
            vol.Required(
                CONF_TRACKER_LATITUDE, default=sensor.get(CONF_TRACKER_LATITUDE, "")
            )
        ] = TextSelector()
        schema[
            vol.Required(
                CONF_TRACKER_LONGITUDE, default=sensor.get(CONF_TRACKER_LONGITUDE, "")
            )
        ] = TextSelector()
        schema[
            vol.Optional(
                CONF_TRACKER_LOCATION_NAME,
                default=sensor.get(CONF_TRACKER_LOCATION_NAME, ""),
            )
        ] = TextSelector()
        schema[
            vol.Optional(
                CONF_TRACKER_SOURCE_TYPE,
                default=sensor.get(CONF_TRACKER_SOURCE_TYPE) or "gps",
            )
        ] = SelectSelector(
            SelectSelectorConfig(
                options=SOURCE_TYPES,
                mode=SelectSelectorMode.DROPDOWN,
                translation_key="tracker_source_type",
            )
        )

    return vol.Schema(schema)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------
def _validate_url(url: str) -> bool:
    """Return True if the URL has a scheme and host."""
    try:
        parsed = urlparse(url)
        return bool(parsed.scheme and parsed.netloc)
    except ValueError:
        return False


def _finalize_sensor_config(
    base: dict[str, Any], user_input: dict[str, Any]
) -> dict[str, Any]:
    """Merge user input into a sensor config and normalize values."""
    sensor_config = dict(base)
    sensor_config.update(user_input)

    # HA forms can return None for empty optional text fields.
    if sensor_config.get(CONF_SENSOR_UNIT) is None:
        sensor_config[CONF_SENSOR_UNIT] = ""

    # Normalize the "no device class" sentinel to an empty string.
    if sensor_config.get(CONF_SENSOR_DEVICE_CLASS) in (None, "none"):
        sensor_config[CONF_SENSOR_DEVICE_CLASS] = ""

    for field in _OPTIONAL_SENSOR_FIELDS:
        sensor_config.setdefault(field, "")

    return sensor_config


def _header_list(headers: list[dict[str, str]]) -> str:
    """Return a bullet list of configured headers."""
    if not headers:
        return "_None_"
    return "\n".join(f"• {h['key']}: {h['value']}" for h in headers)


def _sensor_list(sensors: list[dict[str, Any]]) -> str:
    """Return a bullet list of configured sensors."""
    if not sensors:
        return "_None_"
    return "\n".join(
        f"• {s[CONF_SENSOR_NAME]} "
        f"({SENSOR_TYPES.get(s.get(CONF_SENSOR_TYPE, 'sensor'), 'Sensor')})"
        for s in sensors
    )


# ---------------------------------------------------------------------------
# Config flow
# ---------------------------------------------------------------------------
class HTTPAgentConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HTTP Agent."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self.data: dict[str, Any] = {}
        self.headers: list[dict[str, str]] = []
        self.sensors: list[dict[str, Any]] = []
        self.current_sensor: dict[str, Any] | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step - URL configuration."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not _validate_url(user_input[CONF_URL]):
                errors["base"] = "invalid_url"

            if not errors:
                self.data.update(user_input)
                return await self.async_step_headers()

        return self.async_show_form(
            step_id="user",
            data_schema=_basic_schema(self.data),
            errors=errors,
        )

    async def async_step_headers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the headers menu."""
        return self.async_show_menu(
            step_id="headers",
            menu_options=["add_header", "headers_done"],
            description_placeholders={"headers": _header_list(self.headers)},
        )

    async def async_step_add_header(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a header."""
        if user_input is not None:
            self.headers.append(
                {"key": user_input["key"], "value": user_input["value"]}
            )
            return await self.async_step_headers()

        return self.async_show_form(step_id="add_header", data_schema=_header_schema())

    async def async_step_headers_done(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Store headers and continue to the next step."""
        self.data[CONF_HEADERS] = self.headers
        if self.data[CONF_METHOD] in HTTP_METHODS_WITH_PAYLOAD:
            return await self.async_step_payload()
        return await self.async_step_sensors()

    async def async_step_payload(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle payload configuration."""
        if user_input is not None:
            self.data[CONF_CONTENT_TYPE] = user_input[CONF_CONTENT_TYPE]
            self.data[CONF_PAYLOAD] = user_input.get(CONF_PAYLOAD, "")
            return await self.async_step_sensors()

        return self.async_show_form(
            step_id="payload", data_schema=_payload_schema(self.data)
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the sensors menu."""
        return self.async_show_menu(
            step_id="sensors",
            menu_options=["add_sensor", "sensors_done"],
            description_placeholders={"sensors": _sensor_list(self.sensors)},
        )

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select sensor type and name."""
        if user_input is not None:
            self.current_sensor = {
                CONF_SENSOR_NAME: user_input[CONF_SENSOR_NAME],
                CONF_SENSOR_TYPE: user_input[CONF_SENSOR_TYPE],
            }
            return await self.async_step_sensor_config()

        return self.async_show_form(
            step_id="add_sensor", data_schema=_add_sensor_schema()
        )

    async def async_step_sensor_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure sensor specific settings."""
        assert self.current_sensor is not None
        sensor_type = self.current_sensor[CONF_SENSOR_TYPE]

        if user_input is not None:
            self.sensors.append(
                _finalize_sensor_config(self.current_sensor, user_input)
            )
            self.current_sensor = None
            return await self.async_step_sensors()

        return self.async_show_form(
            step_id="sensor_config",
            data_schema=_sensor_config_schema(sensor_type),
        )

    async def async_step_sensors_done(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Validate sensors and create the entry."""
        if not self.sensors:
            return self.async_abort(reason="no_sensors")

        self.data[CONF_SENSORS] = self.sensors

        parsed_url = urlparse(self.data[CONF_URL])
        unique_id = (
            f"{parsed_url.netloc}{parsed_url.path}{parsed_url.query}".replace("/", "_")
            .replace(".", "_")
            .replace("?", "_")
            .replace("&", "_")
            .replace("=", "_")
        )
        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        title = f"HTTP Agent - {parsed_url.netloc}"
        return self.async_create_entry(title=title, data=self.data)

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HTTPAgentOptionsFlow:
        """Get the options flow for this handler."""
        return HTTPAgentOptionsFlow(config_entry)


# ---------------------------------------------------------------------------
# Options flow
# ---------------------------------------------------------------------------
class HTTPAgentOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HTTP Agent."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        self._config_entry = config_entry

        data = dict(config_entry.data)
        if config_entry.options:
            data.update(config_entry.options)

        self._data: dict[str, Any] = data
        self.headers: list[dict[str, str]] = list(data.get(CONF_HEADERS, []))
        self.sensors: list[dict[str, Any]] = list(data.get(CONF_SENSORS, []))
        self.current_sensor: dict[str, Any] | None = None
        self.selected_sensor_index: int | None = None

    def _save(self) -> ConfigFlowResult:
        """Persist the current configuration as entry options."""
        return self.async_create_entry(title="", data=self._data)

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the main options menu."""
        menu_options = ["basic", "headers"]
        if self._data.get(CONF_METHOD, DEFAULT_METHOD) in HTTP_METHODS_WITH_PAYLOAD:
            menu_options.append("payload")
        menu_options.append("sensors")

        return self.async_show_menu(step_id="init", menu_options=menu_options)

    async def async_step_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit basic settings."""
        errors: dict[str, str] = {}

        if user_input is not None:
            if not _validate_url(user_input[CONF_URL]):
                errors["base"] = "invalid_url"

            if not errors:
                self._data.update(user_input)
                return self._save()

        return self.async_show_form(
            step_id="basic",
            data_schema=_basic_schema(self._data),
            errors=errors,
        )

    async def async_step_headers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the headers menu."""
        return self.async_show_menu(
            step_id="headers",
            menu_options=["add_header", "clear_headers", "headers_done"],
            description_placeholders={"headers": _header_list(self.headers)},
        )

    async def async_step_add_header(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Add a header."""
        if user_input is not None:
            self.headers.append(
                {"key": user_input["key"], "value": user_input["value"]}
            )
            return await self.async_step_headers()

        return self.async_show_form(step_id="add_header", data_schema=_header_schema())

    async def async_step_clear_headers(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Clear all headers."""
        self.headers = []
        return await self.async_step_headers()

    async def async_step_headers_done(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Save headers."""
        self._data[CONF_HEADERS] = self.headers
        return self._save()

    async def async_step_payload(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Edit payload configuration."""
        if user_input is not None:
            self._data[CONF_CONTENT_TYPE] = user_input[CONF_CONTENT_TYPE]
            self._data[CONF_PAYLOAD] = user_input.get(CONF_PAYLOAD, "")
            return self._save()

        return self.async_show_form(
            step_id="payload", data_schema=_payload_schema(self._data)
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the sensors menu."""
        menu_options = ["add_sensor"]
        if self.sensors:
            menu_options += ["select_sensor", "clear_sensors"]
        menu_options.append("sensors_done")

        return self.async_show_menu(
            step_id="sensors",
            menu_options=menu_options,
            description_placeholders={"sensors": _sensor_list(self.sensors)},
        )

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select sensor type and name."""
        if user_input is not None:
            self.current_sensor = {
                CONF_SENSOR_NAME: user_input[CONF_SENSOR_NAME],
                CONF_SENSOR_TYPE: user_input[CONF_SENSOR_TYPE],
            }
            return await self.async_step_sensor_config()

        return self.async_show_form(
            step_id="add_sensor", data_schema=_add_sensor_schema()
        )

    async def async_step_sensor_config(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Configure sensor specific settings."""
        assert self.current_sensor is not None
        sensor_type = self.current_sensor[CONF_SENSOR_TYPE]

        if user_input is not None:
            self.sensors.append(
                _finalize_sensor_config(self.current_sensor, user_input)
            )
            self.current_sensor = None
            return await self.async_step_sensors()

        return self.async_show_form(
            step_id="sensor_config",
            data_schema=_sensor_config_schema(sensor_type),
        )

    async def async_step_clear_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Clear all sensors."""
        self.sensors = []
        return await self.async_step_sensors()

    async def async_step_sensors_done(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Save sensors."""
        if not self.sensors:
            return self.async_abort(reason="no_sensors")
        self._data[CONF_SENSORS] = self.sensors
        return self._save()

    async def async_step_select_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Select a sensor to edit or delete."""
        if user_input is not None:
            selected_sensor = user_input["sensor"]
            self.selected_sensor_index = next(
                i
                for i, s in enumerate(self.sensors)
                if s[CONF_SENSOR_NAME] == selected_sensor
            )
            return await self.async_step_edit_sensor()

        schema = vol.Schema(
            {
                vol.Required("sensor"): SelectSelector(
                    SelectSelectorConfig(
                        options=[s[CONF_SENSOR_NAME] for s in self.sensors],
                        mode=SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )

        return self.async_show_form(step_id="select_sensor", data_schema=schema)

    async def async_step_edit_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the edit/delete menu for a selected sensor."""
        assert self.selected_sensor_index is not None
        sensor = self.sensors[self.selected_sensor_index]
        sensor_type_name = SENSOR_TYPES.get(
            sensor.get(CONF_SENSOR_TYPE, "sensor"), "Sensor"
        )
        sensor_info = (
            f"**{sensor[CONF_SENSOR_NAME]}** ({sensor_type_name})\n"
            f"State: `{sensor.get(CONF_SENSOR_STATE, '')}`"
        )

        return self.async_show_menu(
            step_id="edit_sensor",
            menu_options=["modify_sensor", "delete_sensor", "edit_back"],
            description_placeholders={"sensor_info": sensor_info},
        )

    async def async_step_edit_back(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Return to the sensors menu."""
        self.selected_sensor_index = None
        return await self.async_step_sensors()

    async def async_step_delete_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Delete the selected sensor."""
        if self.selected_sensor_index is not None:
            del self.sensors[self.selected_sensor_index]
            self.selected_sensor_index = None
        return await self.async_step_sensors()

    async def async_step_modify_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Modify the selected sensor."""
        assert self.selected_sensor_index is not None
        sensor = self.sensors[self.selected_sensor_index]
        sensor_type = sensor.get(CONF_SENSOR_TYPE, "sensor")

        if user_input is not None:
            base = {
                CONF_SENSOR_NAME: user_input.get(
                    CONF_SENSOR_NAME, sensor[CONF_SENSOR_NAME]
                ),
                CONF_SENSOR_TYPE: sensor_type,
            }
            self.sensors[self.selected_sensor_index] = _finalize_sensor_config(
                base, user_input
            )
            self.selected_sensor_index = None
            return await self.async_step_sensors()

        return self.async_show_form(
            step_id="modify_sensor",
            data_schema=_sensor_config_schema(sensor_type, sensor, include_name=True),
        )
