"""Config flow for HTTP Agent integration."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult

from .const import (
    BINARY_SENSOR_DEVICE_CLASSES,
    CONF_CONTENT_TYPE,
    CONF_HEADERS,
    CONF_INTERVAL,
    CONF_METHOD,
    CONF_PAYLOAD,
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


class HTTPAgentConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HTTP Agent."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.data = {}
        self.headers = []
        self.sensors = []
        self.current_sensor = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - URL configuration."""
        errors = {}

        if user_input is not None:
            # Validate URL
            try:
                parsed = urlparse(user_input[CONF_URL])
                if not parsed.scheme or not parsed.netloc:
                    errors["base"] = "invalid_url"
            except Exception:
                errors["base"] = "invalid_url"

            if not errors:
                self.data.update(user_input)
                return await self.async_step_headers()

        schema = vol.Schema(
            {
                vol.Required(CONF_URL): str,
                vol.Required(CONF_METHOD, default=DEFAULT_METHOD): vol.In(HTTP_METHODS),
                vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=300)
                ),
                vol.Optional(CONF_INTERVAL, default=DEFAULT_INTERVAL): vol.All(
                    vol.Coerce(int), vol.Range(min=5, max=86400)
                ),
                vol.Optional(CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL): bool,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_headers(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle headers configuration."""
        if user_input is not None:
            action = user_input.get("action")

            if action == "add":
                return await self.async_step_add_header()
            elif action == "done":
                self.data[CONF_HEADERS] = self.headers
                # Check if we need payload step
                if self.data[CONF_METHOD] in HTTP_METHODS_WITH_PAYLOAD:
                    return await self.async_step_payload()
                else:
                    return await self.async_step_sensors()

        header_list = (
            "\n".join([f"• {h['key']}: {h['value']}" for h in self.headers])
            if self.headers
            else ""
        )

        schema = vol.Schema(
            {
                vol.Required("action"): vol.In(["add", "done"]),
            }
        )

        return self.async_show_form(
            step_id="headers",
            data_schema=schema,
            description_placeholders={"headers": header_list},
        )

    async def async_step_add_header(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a header."""
        if user_input is not None:
            self.headers.append(
                {
                    "key": user_input["key"],
                    "value": user_input["value"],
                }
            )
            return await self.async_step_headers()

        schema = vol.Schema(
            {
                vol.Required("key"): str,
                vol.Required("value"): str,
            }
        )

        return self.async_show_form(
            step_id="add_header",
            data_schema=schema,
        )

    async def async_step_payload(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle payload configuration."""
        if user_input is not None:
            self.data[CONF_CONTENT_TYPE] = user_input[CONF_CONTENT_TYPE]
            self.data[CONF_PAYLOAD] = user_input.get(CONF_PAYLOAD, "")
            return await self.async_step_sensors()

        schema = vol.Schema(
            {
                vol.Required(CONF_CONTENT_TYPE, default="application/json"): vol.In(
                    {ct: ct for ct in CONTENT_TYPES}
                ),
                vol.Optional(CONF_PAYLOAD, default=""): str,
            }
        )

        return self.async_show_form(
            step_id="payload",
            data_schema=schema,
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle sensors configuration."""
        if user_input is not None:
            action = user_input.get("action")

            if action == "add":
                return await self.async_step_add_sensor()
            elif action == "done":
                if not self.sensors:
                    return self.async_abort(reason="no_sensors")

                self.data[CONF_SENSORS] = self.sensors

                # Create unique ID based on URL
                parsed_url = urlparse(self.data[CONF_URL])
                unique_id = f"{parsed_url.netloc}{parsed_url.path}".replace(
                    "/", "_"
                ).replace(".", "_")

                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()

                # Create title from URL
                title = f"HTTP Agent - {parsed_url.netloc}"

                return self.async_create_entry(
                    title=title,
                    data=self.data,
                )

        sensor_list = (
            "\n".join(
                [
                    f"• {s[CONF_SENSOR_NAME]} ({SENSOR_TYPES.get(s.get(CONF_SENSOR_TYPE, 'sensor'), 'Sensor')})"
                    for s in self.sensors
                ]
            )
            if self.sensors
            else ""
        )

        schema = vol.Schema(
            {
                vol.Required("action"): vol.In(["add", "done"]),
            }
        )

        return self.async_show_form(
            step_id="sensors",
            data_schema=schema,
            description_placeholders={"sensors": sensor_list},
        )

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select sensor type and name."""
        if user_input is not None:
            # Store sensor type and name for the next step
            self.current_sensor = {
                CONF_SENSOR_NAME: user_input[CONF_SENSOR_NAME],
                CONF_SENSOR_TYPE: user_input[CONF_SENSOR_TYPE],
            }
            return await self.async_step_sensor_config()

        schema = vol.Schema(
            {
                vol.Required(CONF_SENSOR_NAME): str,
                vol.Required(CONF_SENSOR_TYPE): vol.In(SENSOR_TYPES),
            }
        )

        return self.async_show_form(
            step_id="add_sensor",
            data_schema=schema,
        )

    async def async_step_sensor_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure sensor specific settings."""
        if user_input is not None:
            # Merge with existing sensor data
            sensor_config = dict(self.current_sensor)
            sensor_config.update(user_input)

            # Add optional fields that may not be in user_input
            optional_fields = [
                CONF_SENSOR_STATE,
                CONF_SENSOR_ICON,
                CONF_SENSOR_COLOR,
                CONF_SENSOR_DEVICE_CLASS,
                CONF_SENSOR_UNIT,
                CONF_TRACKER_LATITUDE,
                CONF_TRACKER_LONGITUDE,
                CONF_TRACKER_LOCATION_NAME,
                CONF_TRACKER_SOURCE_TYPE,
            ]
            for field in optional_fields:
                if field not in sensor_config:
                    sensor_config[field] = user_input.get(field, "")

            self.sensors.append(sensor_config)
            # Clean up temporary data
            self.current_sensor = None
            return await self.async_step_sensors()

        # Get sensor type to determine what fields to show
        sensor_type = self.current_sensor[CONF_SENSOR_TYPE]

        # Base schema with common fields
        schema_dict = {
            vol.Required(CONF_SENSOR_STATE): str,
            vol.Optional(CONF_SENSOR_ICON, default=""): str,
            vol.Optional(CONF_SENSOR_COLOR, default=""): str,
        }

        # Add device class selection based on sensor type
        if sensor_type == "sensor":
            schema_dict[vol.Optional(CONF_SENSOR_DEVICE_CLASS)] = vol.In(
                ["none"] + list(SENSOR_DEVICE_CLASSES)
            )
            schema_dict[vol.Optional(CONF_SENSOR_UNIT, default="")] = str
        elif sensor_type == "binary_sensor":
            schema_dict[vol.Optional(CONF_SENSOR_DEVICE_CLASS)] = vol.In(
                ["none"] + list(BINARY_SENSOR_DEVICE_CLASSES)
            )
        elif sensor_type == "number":
            schema_dict[vol.Optional(CONF_SENSOR_DEVICE_CLASS)] = vol.In(
                ["none"] + list(NUMBER_DEVICE_CLASSES)
            )
            schema_dict[vol.Optional(CONF_SENSOR_UNIT, default="")] = str
        elif sensor_type == "device_tracker":
            # Device tracker specific fields
            schema_dict[vol.Required(CONF_TRACKER_LATITUDE)] = str
            schema_dict[vol.Required(CONF_TRACKER_LONGITUDE)] = str
            schema_dict[vol.Optional(CONF_TRACKER_LOCATION_NAME, default="")] = str
            schema_dict[vol.Optional(CONF_TRACKER_SOURCE_TYPE, default="gps")] = vol.In(
                ["gps", "router", "bluetooth", "bluetooth_le"]
            )

        schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="sensor_config",
            data_schema=schema,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HTTPAgentOptionsFlow:
        """Get the options flow for this handler."""
        return HTTPAgentOptionsFlow(config_entry)


class HTTPAgentOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for HTTP Agent."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        super().__init__()
        # Start with config entry data and overlay any existing options
        self.data = dict(config_entry.data)
        if config_entry.options:
            self.data.update(config_entry.options)
        self.headers = list(self.data.get(CONF_HEADERS, []))
        self.sensors = list(self.data.get(CONF_SENSORS, []))
        self.current_sensor = None

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show main options menu."""
        if user_input is not None:
            action = user_input.get("action")

            if action == "basic":
                return await self.async_step_basic()
            elif action == "headers":
                return await self.async_step_headers()
            elif action == "payload":
                return await self.async_step_payload()
            elif action == "sensors":
                return await self.async_step_sensors()

        # Build options menu based on current method
        options = ["basic", "headers", "sensors"]

        # Add payload option only for methods that support it
        if self.data.get(CONF_METHOD, DEFAULT_METHOD) in HTTP_METHODS_WITH_PAYLOAD:
            options.insert(2, "payload")

        schema = vol.Schema(
            {
                vol.Required("action"): vol.In(options),
            }
        )

        return self.async_show_form(
            step_id="init",
            data_schema=schema,
        )

    async def async_step_basic(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit basic settings."""
        errors = {}

        if user_input is not None:
            # Validate URL
            try:
                parsed = urlparse(user_input[CONF_URL])
                if not parsed.scheme or not parsed.netloc:
                    errors["base"] = "invalid_url"
            except Exception:
                errors["base"] = "invalid_url"

            if not errors:
                self.data.update(user_input)
                # Save as options, which will trigger reload
                return self.async_create_entry(title="", data=self.data)

        schema = vol.Schema(
            {
                vol.Required(CONF_URL, default=self.data.get(CONF_URL, "")): str,
                vol.Required(
                    CONF_METHOD, default=self.data.get(CONF_METHOD, DEFAULT_METHOD)
                ): vol.In(HTTP_METHODS),
                vol.Optional(
                    CONF_TIMEOUT, default=self.data.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)
                ): vol.All(vol.Coerce(int), vol.Range(min=1, max=300)),
                vol.Optional(
                    CONF_INTERVAL,
                    default=self.data.get(CONF_INTERVAL, DEFAULT_INTERVAL),
                ): vol.All(vol.Coerce(int), vol.Range(min=5, max=86400)),
                vol.Optional(
                    CONF_VERIFY_SSL,
                    default=self.data.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
                ): bool,
            }
        )

        return self.async_show_form(
            step_id="basic",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_headers(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit headers configuration."""
        if user_input is not None:
            action = user_input.get("action")

            if action == "add":
                return await self.async_step_add_header()
            elif action == "clear":
                self.headers = []
                return await self.async_step_headers()
            elif action == "done":
                self.data[CONF_HEADERS] = self.headers
                return self.async_create_entry(title="", data=self.data)

        header_list = (
            "\n".join([f"• {h['key']}: {h['value']}" for h in self.headers])
            if self.headers
            else ""
        )

        schema = vol.Schema(
            {
                vol.Required("action"): vol.In(["add", "clear", "done"]),
            }
        )

        return self.async_show_form(
            step_id="headers",
            data_schema=schema,
            description_placeholders={"headers": header_list},
        )

    async def async_step_add_header(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a header."""
        if user_input is not None:
            self.headers.append(
                {
                    "key": user_input["key"],
                    "value": user_input["value"],
                }
            )
            return await self.async_step_headers()

        schema = vol.Schema(
            {
                vol.Required("key"): str,
                vol.Required("value"): str,
            }
        )

        return self.async_show_form(
            step_id="add_header",
            data_schema=schema,
        )

    async def async_step_payload(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit payload configuration."""
        if user_input is not None:
            self.data[CONF_CONTENT_TYPE] = user_input[CONF_CONTENT_TYPE]
            self.data[CONF_PAYLOAD] = user_input.get(CONF_PAYLOAD, "")
            return self.async_create_entry(title="", data=self.data)

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_CONTENT_TYPE,
                    default=self.data.get(CONF_CONTENT_TYPE, "application/json"),
                ): vol.In({ct: ct for ct in CONTENT_TYPES}),
                vol.Optional(
                    CONF_PAYLOAD, default=self.data.get(CONF_PAYLOAD, "")
                ): str,
            }
        )

        return self.async_show_form(
            step_id="payload",
            data_schema=schema,
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit sensors configuration."""
        if user_input is not None:
            action = user_input.get("action")

            if action == "add":
                return await self.async_step_add_sensor()
            elif action == "edit":
                return await self.async_step_select_sensor()
            elif action == "clear":
                self.sensors = []
                return await self.async_step_sensors()
            elif action == "done":
                if not self.sensors:
                    return self.async_abort(reason="no_sensors")
                self.data[CONF_SENSORS] = self.sensors
                return self.async_create_entry(title="", data=self.data)

        sensor_list = (
            "\n".join(
                [
                    f"• {s[CONF_SENSOR_NAME]} ({SENSOR_TYPES.get(s.get(CONF_SENSOR_TYPE, 'sensor'), 'Sensor')})"
                    for s in self.sensors
                ]
            )
            if self.sensors
            else ""
        )

        # Build action options based on available sensors
        actions = ["add", "done"]
        if self.sensors:
            actions.insert(1, "edit")
            actions.insert(2, "clear")

        schema = vol.Schema(
            {
                vol.Required("action"): vol.In(actions),
            }
        )

        return self.async_show_form(
            step_id="sensors",
            data_schema=schema,
            description_placeholders={"sensors": sensor_list},
        )

    async def async_step_select_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select a sensor to edit or delete."""
        if user_input is not None:
            selected_sensor = user_input["sensor"]
            self.selected_sensor_index = next(
                i
                for i, s in enumerate(self.sensors)
                if s[CONF_SENSOR_NAME] == selected_sensor
            )
            return await self.async_step_edit_sensor()

        sensor_options = {
            s[CONF_SENSOR_NAME]: s[CONF_SENSOR_NAME] for s in self.sensors
        }

        schema = vol.Schema(
            {
                vol.Required("sensor"): vol.In(sensor_options),
            }
        )

        return self.async_show_form(
            step_id="select_sensor",
            data_schema=schema,
        )

    async def async_step_edit_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit or delete a selected sensor."""
        if user_input is not None:
            action = user_input.get("action")

            if action == "edit":
                return await self.async_step_modify_sensor()
            elif action == "delete":
                # Remove the sensor
                del self.sensors[self.selected_sensor_index]
                return await self.async_step_sensors()
            elif action == "back":
                return await self.async_step_sensors()

        sensor = self.sensors[self.selected_sensor_index]
        sensor_name = sensor[CONF_SENSOR_NAME]
        sensor_type = sensor.get(CONF_SENSOR_TYPE, "sensor")
        sensor_state = sensor.get(CONF_SENSOR_STATE, "")

        # Build sensor info string
        sensor_type_name = SENSOR_TYPES.get(sensor_type, "Sensor")
        sensor_info = f"**{sensor_name}** ({sensor_type_name})\nState: `{sensor_state}`"

        schema = vol.Schema(
            {
                vol.Required("action"): vol.In(["edit", "delete", "back"]),
            }
        )

        return self.async_show_form(
            step_id="edit_sensor",
            data_schema=schema,
            description_placeholders={
                "sensor_info": sensor_info,
            },
        )

    async def async_step_modify_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Modify the selected sensor."""
        if user_input is not None:
            # Update the sensor configuration - preserve sensor type
            sensor_config = {
                CONF_SENSOR_NAME: user_input[CONF_SENSOR_NAME],
                CONF_SENSOR_TYPE: self.sensors[self.selected_sensor_index].get(
                    CONF_SENSOR_TYPE, "sensor"
                ),
                CONF_SENSOR_STATE: user_input.get(CONF_SENSOR_STATE, ""),
                CONF_SENSOR_ICON: user_input.get(CONF_SENSOR_ICON, ""),
                CONF_SENSOR_COLOR: user_input.get(CONF_SENSOR_COLOR, ""),
            }

            # Add device class and unit if provided
            if user_input.get(CONF_SENSOR_DEVICE_CLASS):
                sensor_config[CONF_SENSOR_DEVICE_CLASS] = user_input[
                    CONF_SENSOR_DEVICE_CLASS
                ]
            if user_input.get(CONF_SENSOR_UNIT):
                sensor_config[CONF_SENSOR_UNIT] = user_input[CONF_SENSOR_UNIT]

            # Add tracker fields if it's a device tracker
            sensor_type = sensor_config[CONF_SENSOR_TYPE]
            if sensor_type == "device_tracker":
                if user_input.get(CONF_TRACKER_LATITUDE):
                    sensor_config[CONF_TRACKER_LATITUDE] = user_input[
                        CONF_TRACKER_LATITUDE
                    ]
                if user_input.get(CONF_TRACKER_LONGITUDE):
                    sensor_config[CONF_TRACKER_LONGITUDE] = user_input[
                        CONF_TRACKER_LONGITUDE
                    ]
                if user_input.get(CONF_TRACKER_LOCATION_NAME):
                    sensor_config[CONF_TRACKER_LOCATION_NAME] = user_input[
                        CONF_TRACKER_LOCATION_NAME
                    ]
                if user_input.get(CONF_TRACKER_SOURCE_TYPE):
                    sensor_config[CONF_TRACKER_SOURCE_TYPE] = user_input[
                        CONF_TRACKER_SOURCE_TYPE
                    ]

            self.sensors[self.selected_sensor_index] = sensor_config
            return await self.async_step_sensors()

        # Pre-fill with current sensor values
        sensor = self.sensors[self.selected_sensor_index]
        sensor_type = sensor.get(CONF_SENSOR_TYPE, "sensor")

        # Build schema based on sensor type
        schema_dict = {
            vol.Required(CONF_SENSOR_NAME, default=sensor[CONF_SENSOR_NAME]): str,
            vol.Optional(
                CONF_SENSOR_STATE, default=sensor.get(CONF_SENSOR_STATE, "")
            ): str,
            vol.Optional(
                CONF_SENSOR_ICON, default=sensor.get(CONF_SENSOR_ICON, "")
            ): str,
            vol.Optional(
                CONF_SENSOR_COLOR, default=sensor.get(CONF_SENSOR_COLOR, "")
            ): str,
        }

        # Add device class field based on sensor type
        if sensor_type == "sensor":
            device_classes = {"": ""} | {dc: dc for dc in SENSOR_DEVICE_CLASSES}
            schema_dict[
                vol.Optional(
                    CONF_SENSOR_DEVICE_CLASS,
                    default=sensor.get(CONF_SENSOR_DEVICE_CLASS, ""),
                )
            ] = vol.In(device_classes)
            schema_dict[
                vol.Optional(CONF_SENSOR_UNIT, default=sensor.get(CONF_SENSOR_UNIT, ""))
            ] = str
        elif sensor_type == "binary_sensor":
            device_classes = {"": ""} | {dc: dc for dc in BINARY_SENSOR_DEVICE_CLASSES}
            schema_dict[
                vol.Optional(
                    CONF_SENSOR_DEVICE_CLASS,
                    default=sensor.get(CONF_SENSOR_DEVICE_CLASS, ""),
                )
            ] = vol.In(device_classes)
        elif sensor_type == "number":
            device_classes = {"": ""} | {dc: dc for dc in NUMBER_DEVICE_CLASSES}
            schema_dict[
                vol.Optional(
                    CONF_SENSOR_DEVICE_CLASS,
                    default=sensor.get(CONF_SENSOR_DEVICE_CLASS, ""),
                )
            ] = vol.In(device_classes)
            schema_dict[
                vol.Optional(CONF_SENSOR_UNIT, default=sensor.get(CONF_SENSOR_UNIT, ""))
            ] = str
        elif sensor_type == "device_tracker":
            # Add device tracker specific fields
            schema_dict[
                vol.Optional(
                    CONF_TRACKER_LATITUDE, default=sensor.get(CONF_TRACKER_LATITUDE, "")
                )
            ] = str
            schema_dict[
                vol.Optional(
                    CONF_TRACKER_LONGITUDE,
                    default=sensor.get(CONF_TRACKER_LONGITUDE, ""),
                )
            ] = str
            schema_dict[
                vol.Optional(
                    CONF_TRACKER_LOCATION_NAME,
                    default=sensor.get(CONF_TRACKER_LOCATION_NAME, ""),
                )
            ] = str
            schema_dict[
                vol.Optional(
                    CONF_TRACKER_SOURCE_TYPE,
                    default=sensor.get(CONF_TRACKER_SOURCE_TYPE, ""),
                )
            ] = vol.In(["", "gps", "router", "bluetooth", "bluetooth_le"])

        schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="modify_sensor",
            data_schema=schema,
        )

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select sensor type and name."""
        if user_input is not None:
            # Store sensor type and name for the next step
            self.current_sensor = {
                CONF_SENSOR_NAME: user_input[CONF_SENSOR_NAME],
                CONF_SENSOR_TYPE: user_input[CONF_SENSOR_TYPE],
            }
            return await self.async_step_sensor_config()

        schema = vol.Schema(
            {
                vol.Required(CONF_SENSOR_NAME): str,
                vol.Required(CONF_SENSOR_TYPE): vol.In(SENSOR_TYPES),
            }
        )

        return self.async_show_form(
            step_id="add_sensor",
            data_schema=schema,
        )

    async def async_step_sensor_config(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Configure sensor specific settings."""
        if user_input is not None:
            # Merge with existing sensor data
            sensor_config = dict(self.current_sensor)
            sensor_config.update(user_input)

            # Add optional fields that may not be in user_input
            optional_fields = [
                CONF_SENSOR_STATE,
                CONF_SENSOR_ICON,
                CONF_SENSOR_COLOR,
                CONF_SENSOR_DEVICE_CLASS,
                CONF_SENSOR_UNIT,
                CONF_TRACKER_LATITUDE,
                CONF_TRACKER_LONGITUDE,
                CONF_TRACKER_LOCATION_NAME,
                CONF_TRACKER_SOURCE_TYPE,
            ]
            for field in optional_fields:
                if field not in sensor_config:
                    sensor_config[field] = user_input.get(field, "")

            self.sensors.append(sensor_config)
            # Clean up temporary data
            self.current_sensor = None
            return await self.async_step_sensors()

        # Get sensor type to determine what fields to show
        sensor_type = self.current_sensor[CONF_SENSOR_TYPE]

        # Base schema with common fields
        schema_dict = {
            vol.Required(CONF_SENSOR_STATE): str,
            vol.Optional(CONF_SENSOR_ICON, default=""): str,
            vol.Optional(CONF_SENSOR_COLOR, default=""): str,
        }

        # Add device class selection based on sensor type
        if sensor_type == "sensor":
            schema_dict[vol.Optional(CONF_SENSOR_DEVICE_CLASS)] = vol.In(
                ["none"] + list(SENSOR_DEVICE_CLASSES)
            )
            schema_dict[vol.Optional(CONF_SENSOR_UNIT, default="")] = str
        elif sensor_type == "binary_sensor":
            schema_dict[vol.Optional(CONF_SENSOR_DEVICE_CLASS)] = vol.In(
                ["none"] + list(BINARY_SENSOR_DEVICE_CLASSES)
            )
        elif sensor_type == "number":
            schema_dict[vol.Optional(CONF_SENSOR_DEVICE_CLASS)] = vol.In(
                ["none"] + list(NUMBER_DEVICE_CLASSES)
            )
            schema_dict[vol.Optional(CONF_SENSOR_UNIT, default="")] = str
        elif sensor_type == "device_tracker":
            # Device tracker specific fields
            schema_dict[vol.Required(CONF_TRACKER_LATITUDE)] = str
            schema_dict[vol.Required(CONF_TRACKER_LONGITUDE)] = str
            schema_dict[vol.Optional(CONF_TRACKER_LOCATION_NAME, default="")] = str
            schema_dict[vol.Optional(CONF_TRACKER_SOURCE_TYPE, default="gps")] = vol.In(
                ["gps", "router", "bluetooth", "bluetooth_le"]
            )

        schema = vol.Schema(schema_dict)

        return self.async_show_form(
            step_id="sensor_config",
            data_schema=schema,
        )
