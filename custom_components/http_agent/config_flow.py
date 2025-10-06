"""Config flow for HTTP Agent integration."""
from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_NAME, CONF_URL, CONF_PORT, CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
import homeassistant.helpers.config_validation as cv

from .const import (
    DOMAIN,
    CONF_SSL_VERIFY,
    CONF_TIMEOUT,
    CONF_INTERVAL,
    CONF_METHOD,
    CONF_PAYLOAD,
    CONF_QUERYSTRING,
    CONF_ENABLED,
    CONF_SENSORS,
    DEFAULT_TIMEOUT,
    DEFAULT_INTERVAL,
    DEFAULT_SSL_VERIFY,
    DEFAULT_METHOD,
)

_LOGGER = logging.getLogger(__name__)


class HTTPAgentConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for HTTP Agent."""

    VERSION = 1

    def __init__(self):
        """Initialize the config flow."""
        self.data = {}
        self.sensors = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
        errors = {}

        if user_input is not None:
            self.data.update(user_input)
            return await self.async_step_sensors()

        schema = vol.Schema({
            vol.Required(CONF_NAME, default="HTTP Agent"): str,
        })

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_sensors(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the sensors configuration step."""
        if user_input is not None:
            if user_input.get("add_sensor"):
                return await self.async_step_add_sensor()
            else:
                # Create entry
                self.data[CONF_SENSORS] = self.sensors
                return self.async_create_entry(
                    title=self.data[CONF_NAME],
                    data=self.data,
                )

        # Show current sensors and option to add more
        sensor_list = "\n".join([f"• {sensor[CONF_NAME]}" for sensor in self.sensors])
        
        schema = vol.Schema({
            vol.Optional("add_sensor", default=False): bool,
        })

        return self.async_show_form(
            step_id="sensors",
            data_schema=schema,
            description_placeholders={
                "sensor_list": sensor_list or "No sensors configured"
            },
        )

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle adding a sensor."""
        errors = {}

        if user_input is not None:
            # Validate the sensor configuration
            try:
                sensor_config = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_URL: user_input[CONF_URL],
                    CONF_METHOD: user_input.get(CONF_METHOD, DEFAULT_METHOD),
                    CONF_INTERVAL: user_input.get(CONF_INTERVAL, DEFAULT_INTERVAL),
                    CONF_TIMEOUT: user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                    CONF_SSL_VERIFY: user_input.get(CONF_SSL_VERIFY, DEFAULT_SSL_VERIFY),
                    CONF_ENABLED: user_input.get(CONF_ENABLED, True),
                    CONF_PAYLOAD: user_input.get(CONF_PAYLOAD, ""),
                    CONF_QUERYSTRING: user_input.get(CONF_QUERYSTRING, ""),
                }
                self.sensors.append(sensor_config)
                return await self.async_step_sensors()
            except Exception:
                errors["base"] = "invalid_sensor"

        schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_URL): str,
            vol.Optional(CONF_METHOD, default=DEFAULT_METHOD): vol.In(
                ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]
            ),
            vol.Optional(CONF_INTERVAL, default=DEFAULT_INTERVAL): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=86400)
            ),
            vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=300)
            ),
            vol.Optional(CONF_SSL_VERIFY, default=DEFAULT_SSL_VERIFY): bool,
            vol.Optional(CONF_ENABLED, default=True): bool,
            vol.Optional(CONF_PAYLOAD, default=""): str,
            vol.Optional(CONF_QUERYSTRING, default=""): str,
        })

        return self.async_show_form(
            step_id="add_sensor",
            data_schema=schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> HTTPAgentOptionsFlow:
        """Get the options flow for this handler."""
        return HTTPAgentOptionsFlow(config_entry)


class HTTPAgentOptionsFlow(config_entries.OptionsFlow):
    """Handle HTTP Agent options."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.sensors = list(config_entry.data.get(CONF_SENSORS, []))

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        return await self.async_step_sensors_menu()

    async def async_step_sensors_menu(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Show sensors management menu."""
        if user_input is not None:
            if user_input["action"] == "add":
                return await self.async_step_add_sensor()
            elif user_input["action"] == "edit":
                return await self.async_step_select_sensor()
            elif user_input["action"] == "delete":
                return await self.async_step_delete_sensor()
            else:  # done
                return self.async_create_entry(
                    title="",
                    data={CONF_SENSORS: self.sensors},
                )

        sensor_list = "\n".join([f"• {sensor[CONF_NAME]}" for sensor in self.sensors])

        schema = vol.Schema({
            vol.Required("action"): vol.In({
                "add": "Add new sensor",
                "edit": "Edit existing sensor",
                "delete": "Delete sensor",
                "done": "Save and exit",
            }),
        })

        return self.async_show_form(
            step_id="sensors_menu",
            data_schema=schema,
            description_placeholders={
                "sensor_list": sensor_list or "No sensors configured"
            },
        )

    async def async_step_add_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Add a new sensor."""
        errors = {}

        if user_input is not None:
            try:
                sensor_config = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_URL: user_input[CONF_URL],
                    CONF_METHOD: user_input.get(CONF_METHOD, DEFAULT_METHOD),
                    CONF_INTERVAL: user_input.get(CONF_INTERVAL, DEFAULT_INTERVAL),
                    CONF_TIMEOUT: user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                    CONF_SSL_VERIFY: user_input.get(CONF_SSL_VERIFY, DEFAULT_SSL_VERIFY),
                    CONF_ENABLED: user_input.get(CONF_ENABLED, True),
                    CONF_PAYLOAD: user_input.get(CONF_PAYLOAD, ""),
                    CONF_QUERYSTRING: user_input.get(CONF_QUERYSTRING, ""),
                }
                self.sensors.append(sensor_config)
                return await self.async_step_sensors_menu()
            except Exception:
                errors["base"] = "invalid_sensor"

        schema = vol.Schema({
            vol.Required(CONF_NAME): str,
            vol.Required(CONF_URL): str,
            vol.Optional(CONF_METHOD, default=DEFAULT_METHOD): vol.In(
                ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]
            ),
            vol.Optional(CONF_INTERVAL, default=DEFAULT_INTERVAL): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=86400)
            ),
            vol.Optional(CONF_TIMEOUT, default=DEFAULT_TIMEOUT): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=300)
            ),
            vol.Optional(CONF_SSL_VERIFY, default=DEFAULT_SSL_VERIFY): bool,
            vol.Optional(CONF_ENABLED, default=True): bool,
            vol.Optional(CONF_PAYLOAD, default=""): str,
            vol.Optional(CONF_QUERYSTRING, default=""): str,
        })

        return self.async_show_form(
            step_id="add_sensor",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_select_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Select sensor to edit."""
        if user_input is not None:
            self._selected_sensor_idx = int(user_input["sensor"])
            return await self.async_step_edit_sensor()

        if not self.sensors:
            return await self.async_step_sensors_menu()

        sensor_options = {
            str(idx): sensor[CONF_NAME] for idx, sensor in enumerate(self.sensors)
        }

        schema = vol.Schema({
            vol.Required("sensor"): vol.In(sensor_options),
        })

        return self.async_show_form(
            step_id="select_sensor",
            data_schema=schema,
        )

    async def async_step_edit_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Edit selected sensor."""
        sensor = self.sensors[self._selected_sensor_idx]
        errors = {}

        if user_input is not None:
            try:
                self.sensors[self._selected_sensor_idx] = {
                    CONF_NAME: user_input[CONF_NAME],
                    CONF_URL: user_input[CONF_URL],
                    CONF_METHOD: user_input.get(CONF_METHOD, DEFAULT_METHOD),
                    CONF_INTERVAL: user_input.get(CONF_INTERVAL, DEFAULT_INTERVAL),
                    CONF_TIMEOUT: user_input.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
                    CONF_SSL_VERIFY: user_input.get(CONF_SSL_VERIFY, DEFAULT_SSL_VERIFY),
                    CONF_ENABLED: user_input.get(CONF_ENABLED, True),
                    CONF_PAYLOAD: user_input.get(CONF_PAYLOAD, ""),
                    CONF_QUERYSTRING: user_input.get(CONF_QUERYSTRING, ""),
                }
                return await self.async_step_sensors_menu()
            except Exception:
                errors["base"] = "invalid_sensor"

        schema = vol.Schema({
            vol.Required(CONF_NAME, default=sensor.get(CONF_NAME, "")): str,
            vol.Required(CONF_URL, default=sensor.get(CONF_URL, "")): str,
            vol.Optional(CONF_METHOD, default=sensor.get(CONF_METHOD, DEFAULT_METHOD)): vol.In(
                ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD"]
            ),
            vol.Optional(CONF_INTERVAL, default=sensor.get(CONF_INTERVAL, DEFAULT_INTERVAL)): vol.All(
                vol.Coerce(int), vol.Range(min=5, max=86400)
            ),
            vol.Optional(CONF_TIMEOUT, default=sensor.get(CONF_TIMEOUT, DEFAULT_TIMEOUT)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=300)
            ),
            vol.Optional(CONF_SSL_VERIFY, default=sensor.get(CONF_SSL_VERIFY, DEFAULT_SSL_VERIFY)): bool,
            vol.Optional(CONF_ENABLED, default=sensor.get(CONF_ENABLED, True)): bool,
            vol.Optional(CONF_PAYLOAD, default=sensor.get(CONF_PAYLOAD, "")): str,
            vol.Optional(CONF_QUERYSTRING, default=sensor.get(CONF_QUERYSTRING, "")): str,
        })

        return self.async_show_form(
            step_id="edit_sensor",
            data_schema=schema,
            errors=errors,
        )

    async def async_step_delete_sensor(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Delete a sensor."""
        if user_input is not None:
            if "sensor" in user_input:
                sensor_idx = int(user_input["sensor"])
                self.sensors.pop(sensor_idx)
            return await self.async_step_sensors_menu()

        if not self.sensors:
            return await self.async_step_sensors_menu()

        sensor_options = {
            str(idx): sensor[CONF_NAME] for idx, sensor in enumerate(self.sensors)
        }

        schema = vol.Schema({
            vol.Required("sensor"): vol.In(sensor_options),
        })

        return self.async_show_form(
            step_id="delete_sensor",
            data_schema=schema,
        )