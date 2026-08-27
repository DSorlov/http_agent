"""Config flow for the HTTP Agent integration."""

from __future__ import annotations

from abc import abstractmethod
from collections.abc import Mapping
import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import (
    SOURCE_RECONFIGURE,
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    ConfigSubentry,
    ConfigSubentryData,
    ConfigSubentryFlow,
    SubentryFlowResult,
)
from homeassistant.const import (
    CONF_API_KEY,
    CONF_DEVICE_CLASS,
    CONF_HEADERS,
    CONF_ICON,
    CONF_METHOD,
    CONF_NAME,
    CONF_PASSWORD,
    CONF_PAYLOAD,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_TOKEN,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_URL,
    CONF_USERNAME,
    CONF_VERIFY_SSL,
)
from homeassistant.core import callback
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    BooleanSelector,
    IconSelector,
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)

from .api import (
    CannotConnect,
    EmptyResponse,
    InvalidAuth,
    InvalidResponse,
    async_request,
)
from .const import (
    AUTH_API_KEY,
    AUTH_BASIC,
    AUTH_BEARER,
    AUTH_NONE,
    AUTH_TYPES,
    CONF_API_KEY_HEADER,
    CONF_ATTRIBUTES,
    CONF_AUTH_TYPE,
    CONF_CONTENT_TYPE,
    CONF_FOLLOW_REDIRECTS,
    CONF_GPS_ACCURACY_PATH,
    CONF_LATITUDE_PATH,
    CONF_LONGITUDE_PATH,
    CONF_PAYLOAD_OFF,
    CONF_PAYLOAD_ON,
    CONF_RESPONSE_FORMAT,
    CONF_RETRIES,
    CONF_SELECTED_VALUES,
    CONF_SOURCE_TYPE,
    CONF_STATE_CLASS,
    CONF_VALUE_PATH,
    CONFIG_MINOR_VERSION,
    CONFIG_VERSION,
    CONTENT_TYPES,
    DEFAULT_API_KEY_HEADER,
    DEFAULT_CONTENT_TYPE,
    DEFAULT_FOLLOW_REDIRECTS,
    DEFAULT_METHOD,
    DEFAULT_RETRIES,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DEFAULT_VERIFY_SSL,
    DOMAIN,
    FORMAT_AUTO,
    HTTP_METHODS,
    MAX_PREVIEW_LENGTH,
    MAX_RETRIES,
    MAX_SCAN_INTERVAL,
    MAX_TIMEOUT,
    METHODS_WITH_BODY,
    MIN_SCAN_INTERVAL,
    MIN_TIMEOUT,
    RESPONSE_FORMATS,
    SOURCE_TYPES,
    SUBENTRY_TYPE_BINARY_SENSOR,
    SUBENTRY_TYPE_DEVICE_TRACKER,
    SUBENTRY_TYPE_SENSOR,
)
from .discovery import DiscoveredValue, discover_values
from .parser import ParsedResponse

_LOGGER = logging.getLogger(__name__)

SECTION_ADVANCED = "advanced"
SECTION_OPTIONS = "options"

_SCAN_INTERVAL_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=MIN_SCAN_INTERVAL,
        max=MAX_SCAN_INTERVAL,
        step=1,
        mode=NumberSelectorMode.BOX,
        unit_of_measurement="s",
    )
)
_TIMEOUT_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=MIN_TIMEOUT,
        max=MAX_TIMEOUT,
        step=1,
        mode=NumberSelectorMode.BOX,
        unit_of_measurement="s",
    )
)
_RETRIES_SELECTOR = NumberSelector(
    NumberSelectorConfig(min=0, max=MAX_RETRIES, step=1, mode=NumberSelectorMode.BOX)
)
_MULTILINE = TextSelector(TextSelectorConfig(multiline=True))
_PASSWORD = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))


def _options(values: list[str], *, humanise: bool = True) -> list[SelectOptionDict]:
    """Build dropdown options, optionally with human readable labels."""
    return [
        SelectOptionDict(
            value=value,
            label=value.replace("_", " ").capitalize() if humanise else value,
        )
        for value in values
    ]


def _select(values: list[str], **kwargs: Any) -> SelectSelector:
    """Build a single-choice dropdown for a list of raw values."""
    return SelectSelector(
        SelectSelectorConfig(
            options=_options(values), mode=SelectSelectorMode.DROPDOWN, **kwargs
        )
    )


def parse_key_values(text: str | None) -> dict[str, str]:
    """Parse a ``Name: value`` per line block into a dictionary.

    Raises:
        vol.Invalid: If a non-empty line does not contain a colon.

    """
    result: dict[str, str] = {}
    for line in (text or "").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            raise vol.Invalid(f"Missing ':' in line: {stripped}")
        key, value = stripped.split(":", 1)
        if not (key := key.strip()):
            raise vol.Invalid(f"Missing name in line: {stripped}")
        result[key] = value.strip()
    return result


def format_key_values(values: Mapping[str, str] | str | None) -> str:
    """Render a dictionary back into a ``Name: value`` per line block."""
    if isinstance(values, str):
        return values
    return "\n".join(f"{key}: {value}" for key, value in (values or {}).items())


def flatten_sections(user_input: dict[str, Any]) -> dict[str, Any]:
    """Flatten collapsible form sections into a single level dictionary."""
    flattened: dict[str, Any] = {}
    for key, value in user_input.items():
        if key in (SECTION_ADVANCED, SECTION_OPTIONS) and isinstance(value, dict):
            flattened.update(value)
        else:
            flattened[key] = value
    return flattened


class HTTPAgentConfigFlow(ConfigFlow, domain=DOMAIN):
    """Guide the user through configuring one HTTP endpoint."""

    VERSION = CONFIG_VERSION
    MINOR_VERSION = CONFIG_MINOR_VERSION

    def __init__(self) -> None:
        """Initialise the flow state."""
        self._config: dict[str, Any] = {}
        self._response: ParsedResponse | None = None
        self._values: list[DiscoveredValue] = []

    # ------------------------------------------------------------------
    # Step 1 - the endpoint itself
    # ------------------------------------------------------------------
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the endpoint URL, method and authentication style."""
        errors: dict[str, str] = {}

        if user_input is not None:
            try:
                self._config.update(self._parse_endpoint(user_input))
            except vol.Invalid:
                errors["base"] = "invalid_headers"
            else:
                if not _is_valid_url(self._config[CONF_URL]):
                    errors[CONF_URL] = "invalid_url"
                else:
                    return await self._async_continue_from("user")

        defaults = self._config or (
            dict(self._get_reconfigure_entry().data)
            if self.source == SOURCE_RECONFIGURE
            else {}
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _endpoint_schema(), _endpoint_suggestions(defaults)
            ),
            errors=errors,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user change the endpoint of an existing entry."""
        return await self.async_step_user(user_input)

    # ------------------------------------------------------------------
    # Step 2 - credentials, only shown for the chosen auth preset
    # ------------------------------------------------------------------
    async def async_step_credentials(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect credentials for the selected authentication preset."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self._config.update(user_input)
            return await self._async_continue_from("credentials")

        return self.async_show_form(
            step_id="credentials",
            data_schema=self.add_suggested_values_to_schema(
                _credentials_schema(self._config[CONF_AUTH_TYPE]), self._config
            ),
            errors=errors,
            description_placeholders={"auth_type": self._config[CONF_AUTH_TYPE]},
        )

    # ------------------------------------------------------------------
    # Step 3 - request body, only for methods that carry one
    # ------------------------------------------------------------------
    async def async_step_body(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Collect the request body for POST/PUT/PATCH/DELETE."""
        if user_input is not None:
            self._config.update(user_input)
            return await self._async_continue_from("body")

        return self.async_show_form(
            step_id="body",
            data_schema=self.add_suggested_values_to_schema(
                _body_schema(), self._config
            ),
            description_placeholders={"method": self._config[CONF_METHOD]},
        )

    # ------------------------------------------------------------------
    # Step 4 - pick the values that should become entities
    # ------------------------------------------------------------------
    async def async_step_select_values(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show the discovered values and create entities for the chosen ones."""
        if user_input is not None:
            selected: list[str] = user_input.get(CONF_SELECTED_VALUES) or []
            by_path = {value.path: value for value in self._values}
            subentries = [
                _subentry_for(by_path.get(path) or DiscoveredValue(path=path, value=""))
                for path in selected
            ]
            return self.async_create_entry(
                title=self._config[CONF_NAME],
                data=self._config,
                subentries=subentries,
            )

        return self.async_show_form(
            step_id="select_values",
            data_schema=vol.Schema(
                {
                    vol.Optional(CONF_SELECTED_VALUES, default=[]): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(value=value.path, label=value.label)
                                for value in self._values
                            ],
                            multiple=True,
                            custom_value=True,
                            sort=False,
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    )
                }
            ),
            description_placeholders=self._preview_placeholders(),
        )

    # ------------------------------------------------------------------
    # Reauthentication
    # ------------------------------------------------------------------
    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication after the endpoint rejected the credentials."""
        self._config = dict(entry_data)
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for fresh credentials and verify them."""
        errors: dict[str, str] = {}
        auth_type = self._config.get(CONF_AUTH_TYPE, AUTH_NONE)

        if user_input is not None:
            self._config.update(user_input)
            if not (errors := await self._async_test_connection()):
                return self.async_update_reload_and_abort(
                    self._get_reauth_entry(), data=self._config
                )

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=_credentials_schema(auth_type),
            errors=errors,
            description_placeholders={"auth_type": auth_type},
        )

    # ------------------------------------------------------------------
    # Subentries
    # ------------------------------------------------------------------
    @classmethod
    @callback
    def async_get_supported_subentry_types(
        cls, config_entry: ConfigEntry
    ) -> dict[str, type[ConfigSubentryFlow]]:
        """Return the entity types that can be added to an endpoint."""
        return {
            SUBENTRY_TYPE_SENSOR: SensorSubentryFlowHandler,
            SUBENTRY_TYPE_BINARY_SENSOR: BinarySensorSubentryFlowHandler,
            SUBENTRY_TYPE_DEVICE_TRACKER: DeviceTrackerSubentryFlowHandler,
        }

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------
    def _parse_endpoint(self, user_input: dict[str, Any]) -> dict[str, Any]:
        """Normalise the endpoint form into config entry data."""
        config = flatten_sections(user_input)
        config[CONF_URL] = config[CONF_URL].strip()
        config[CONF_METHOD] = config[CONF_METHOD].upper()
        config[CONF_HEADERS] = parse_key_values(config.pop("extra_headers", ""))
        config[CONF_SCAN_INTERVAL] = int(config[CONF_SCAN_INTERVAL])
        config[CONF_TIMEOUT] = int(config[CONF_TIMEOUT])
        config[CONF_RETRIES] = int(config[CONF_RETRIES])
        if not config.get(CONF_NAME):
            config[CONF_NAME] = urlparse(config[CONF_URL]).netloc or DOMAIN
        return config

    async def _async_continue_from(self, step: str) -> ConfigFlowResult:
        """Move to the next required step, or run the live test when done."""
        if step == "user" and self._config[CONF_AUTH_TYPE] != AUTH_NONE:
            return await self.async_step_credentials()
        if (
            step in ("user", "credentials")
            and self._config[CONF_METHOD] in METHODS_WITH_BODY
        ):
            return await self.async_step_body()
        return await self._async_finish(step)

    async def _async_finish(self, step: str) -> ConfigFlowResult:
        """Run the test request and either finish or re-show ``step``."""
        if errors := await self._async_test_connection():
            return await self._async_show_step_again(step, errors)

        if self.source == SOURCE_RECONFIGURE:
            return self.async_update_reload_and_abort(
                self._get_reconfigure_entry(),
                data=self._config,
                title=self._config[CONF_NAME],
            )

        self._async_abort_entries_match(
            {CONF_URL: self._config[CONF_URL], CONF_METHOD: self._config[CONF_METHOD]}
        )
        return await self.async_step_select_values()

    async def _async_test_connection(self) -> dict[str, str]:
        """Perform the live request and remember the discovered values."""
        try:
            self._response = await async_request(self.hass, self._config)
        except InvalidAuth:
            return {"base": "invalid_auth"}
        except EmptyResponse:
            return {"base": "no_values"}
        except InvalidResponse as err:
            _LOGGER.debug("Test request failed: %s", err)
            return {"base": "bad_status"}
        except CannotConnect as err:
            _LOGGER.debug("Test request failed: %s", err)
            return {"base": "cannot_connect"}

        self._values = discover_values(self._response)
        if not self._values:
            return {"base": "no_values"}
        return {}

    async def _async_show_step_again(
        self, step: str, errors: dict[str, str]
    ) -> ConfigFlowResult:
        """Re-render the form the user just submitted, with errors attached."""
        if step == "credentials":
            return self.async_show_form(
                step_id="credentials",
                data_schema=self.add_suggested_values_to_schema(
                    _credentials_schema(self._config[CONF_AUTH_TYPE]), self._config
                ),
                errors=errors,
                description_placeholders={"auth_type": self._config[CONF_AUTH_TYPE]},
            )
        if step == "body":
            return self.async_show_form(
                step_id="body",
                data_schema=self.add_suggested_values_to_schema(
                    _body_schema(), self._config
                ),
                errors=errors,
                description_placeholders={"method": self._config[CONF_METHOD]},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                _endpoint_schema(), _endpoint_suggestions(self._config)
            ),
            errors=errors,
        )

    def _preview_placeholders(self) -> dict[str, str]:
        """Return the response summary shown above the value picker."""
        if self._response is None:
            return {"status": "", "format": "", "count": "0", "preview": ""}
        preview = self._response.text.strip()
        if len(preview) > MAX_PREVIEW_LENGTH:
            preview = f"{preview[:MAX_PREVIEW_LENGTH]}\n…"
        return {
            "status": str(self._response.status),
            "format": self._response.format.upper(),
            "count": str(len(self._values)),
            "preview": preview,
        }


# ----------------------------------------------------------------------
# Schemas
# ----------------------------------------------------------------------
def _endpoint_schema() -> vol.Schema:
    """Return the schema for the endpoint step."""
    return vol.Schema(
        {
            vol.Required(CONF_URL): TextSelector(
                TextSelectorConfig(type=TextSelectorType.URL)
            ),
            vol.Required(CONF_METHOD, default=DEFAULT_METHOD): _select(
                HTTP_METHODS, sort=False
            ),
            vol.Required(CONF_AUTH_TYPE, default=AUTH_NONE): _select(
                AUTH_TYPES, sort=False
            ),
            vol.Optional(CONF_NAME): TextSelector(),
            vol.Required(SECTION_ADVANCED): section(
                vol.Schema(
                    {
                        vol.Optional(
                            CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL
                        ): _SCAN_INTERVAL_SELECTOR,
                        vol.Optional(
                            CONF_TIMEOUT, default=DEFAULT_TIMEOUT
                        ): _TIMEOUT_SELECTOR,
                        vol.Optional(
                            CONF_RETRIES, default=DEFAULT_RETRIES
                        ): _RETRIES_SELECTOR,
                        vol.Optional("extra_headers", default=""): _MULTILINE,
                        vol.Optional(
                            CONF_RESPONSE_FORMAT, default=FORMAT_AUTO
                        ): _select(RESPONSE_FORMATS, sort=False),
                        vol.Optional(
                            CONF_VERIFY_SSL, default=DEFAULT_VERIFY_SSL
                        ): BooleanSelector(),
                        vol.Optional(
                            CONF_FOLLOW_REDIRECTS, default=DEFAULT_FOLLOW_REDIRECTS
                        ): BooleanSelector(),
                    }
                ),
                {"collapsed": True},
            ),
        }
    )


def _endpoint_suggestions(defaults: Mapping[str, Any]) -> dict[str, Any]:
    """Map stored config entry data onto the sectioned endpoint schema."""
    if not defaults:
        return {}
    return {
        CONF_URL: defaults.get(CONF_URL),
        CONF_METHOD: defaults.get(CONF_METHOD, DEFAULT_METHOD),
        CONF_AUTH_TYPE: defaults.get(CONF_AUTH_TYPE, AUTH_NONE),
        CONF_NAME: defaults.get(CONF_NAME),
        SECTION_ADVANCED: {
            CONF_SCAN_INTERVAL: defaults.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL),
            CONF_TIMEOUT: defaults.get(CONF_TIMEOUT, DEFAULT_TIMEOUT),
            CONF_RETRIES: defaults.get(CONF_RETRIES, DEFAULT_RETRIES),
            "extra_headers": format_key_values(defaults.get(CONF_HEADERS)),
            CONF_RESPONSE_FORMAT: defaults.get(CONF_RESPONSE_FORMAT, FORMAT_AUTO),
            CONF_VERIFY_SSL: defaults.get(CONF_VERIFY_SSL, DEFAULT_VERIFY_SSL),
            CONF_FOLLOW_REDIRECTS: defaults.get(
                CONF_FOLLOW_REDIRECTS, DEFAULT_FOLLOW_REDIRECTS
            ),
        },
    }


def _credentials_schema(auth_type: str) -> vol.Schema:
    """Return the credential schema matching the selected auth preset."""
    if auth_type == AUTH_BEARER:
        return vol.Schema({vol.Required(CONF_TOKEN): _PASSWORD})
    if auth_type == AUTH_API_KEY:
        return vol.Schema(
            {
                vol.Required(CONF_API_KEY): _PASSWORD,
                vol.Required(
                    CONF_API_KEY_HEADER, default=DEFAULT_API_KEY_HEADER
                ): TextSelector(),
            }
        )
    if auth_type == AUTH_BASIC:
        return vol.Schema(
            {
                vol.Required(CONF_USERNAME): TextSelector(),
                vol.Required(CONF_PASSWORD): _PASSWORD,
            }
        )
    return vol.Schema({})


def _body_schema() -> vol.Schema:
    """Return the schema for the request body step."""
    return vol.Schema(
        {
            vol.Required(CONF_CONTENT_TYPE, default=DEFAULT_CONTENT_TYPE): _select(
                CONTENT_TYPES, sort=False
            ),
            vol.Optional(CONF_PAYLOAD, default=""): _MULTILINE,
        }
    )


def _subentry_for(value: DiscoveredValue) -> ConfigSubentryData:
    """Build a subentry for a value picked in the config flow."""
    data: dict[str, Any] = {
        CONF_NAME: value.name,
        CONF_VALUE_PATH: value.path,
    }
    if device_class := value.suggested_device_class:
        data[CONF_DEVICE_CLASS] = device_class
    if unit := value.suggested_unit:
        data[CONF_UNIT_OF_MEASUREMENT] = unit
    if state_class := value.suggested_state_class:
        data[CONF_STATE_CLASS] = state_class

    return ConfigSubentryData(
        data=data,
        subentry_type=value.suggested_platform,
        title=value.name,
        unique_id=None,
    )


def _is_valid_url(url: str) -> bool:
    """Return True for absolute http(s) URLs (templates are allowed)."""
    if "{" in url:
        return True
    parsed = urlparse(url)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


# ----------------------------------------------------------------------
# Subentry flows
# ----------------------------------------------------------------------
class HTTPAgentSubentryFlow(ConfigSubentryFlow):
    """Shared behaviour for adding and reconfiguring an entity."""

    @abstractmethod
    def schema(self) -> vol.Schema:
        """Return the form schema for this entity type."""

    def _value_selector(self, *, multiple: bool = False) -> SelectSelector:
        """Return a picker listing the values found in the latest response."""
        options: list[SelectOptionDict] = []
        entry = self._get_entry()
        if (coordinator := getattr(entry, "runtime_data", None)) is not None and (
            response := coordinator.data
        ) is not None:
            options = [
                SelectOptionDict(value=value.path, label=value.label)
                for value in discover_values(response)
            ]
        return SelectSelector(
            SelectSelectorConfig(
                options=options,
                custom_value=True,
                multiple=multiple,
                sort=False,
                mode=SelectSelectorMode.DROPDOWN,
            )
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Add a new entity."""
        return await self._async_form(user_input, {})

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> SubentryFlowResult:
        """Change an existing entity."""
        return await self._async_form(user_input, self._get_reconfigure_subentry())

    async def _async_form(
        self,
        user_input: dict[str, Any] | None,
        subentry: ConfigSubentry | Mapping[str, Any],
    ) -> SubentryFlowResult:
        """Render and process the entity form."""
        errors: dict[str, str] = {}
        existing = (
            dict(subentry.data)
            if isinstance(subentry, ConfigSubentry)
            else dict(subentry)
        )

        if user_input is not None:
            data = flatten_sections(user_input)
            try:
                data[CONF_ATTRIBUTES] = parse_key_values(data.pop(CONF_ATTRIBUTES, ""))
            except vol.Invalid:
                errors["base"] = "invalid_attributes"
            else:
                data = {
                    key: value for key, value in data.items() if value not in ("", {})
                }
                if isinstance(subentry, ConfigSubentry):
                    return self.async_update_and_abort(
                        self._get_entry(),
                        subentry,
                        data=data,
                        title=data[CONF_NAME],
                    )
                return self.async_create_entry(title=data[CONF_NAME], data=data)
            existing = flatten_sections(user_input)

        return self.async_show_form(
            step_id="reconfigure" if isinstance(subentry, ConfigSubentry) else "user",
            data_schema=self.add_suggested_values_to_schema(
                self.schema(), _entity_suggestions(existing)
            ),
            errors=errors,
        )


def _entity_suggestions(data: Mapping[str, Any]) -> dict[str, Any]:
    """Map stored subentry data onto the sectioned entity schema."""
    if not data:
        return {}
    suggestions = {key: value for key, value in data.items() if key != CONF_ATTRIBUTES}
    section_keys = (
        CONF_DEVICE_CLASS,
        CONF_UNIT_OF_MEASUREMENT,
        CONF_STATE_CLASS,
        CONF_ICON,
        CONF_PAYLOAD_ON,
        CONF_PAYLOAD_OFF,
        CONF_GPS_ACCURACY_PATH,
        CONF_SOURCE_TYPE,
    )
    nested = {key: suggestions.pop(key) for key in section_keys if key in suggestions}
    nested[CONF_ATTRIBUTES] = format_key_values(data.get(CONF_ATTRIBUTES))
    suggestions[SECTION_OPTIONS] = nested
    return suggestions


class SensorSubentryFlowHandler(HTTPAgentSubentryFlow):
    """Add or reconfigure a sensor."""

    def schema(self) -> vol.Schema:
        """Return the sensor form schema."""
        return vol.Schema(
            {
                vol.Required(CONF_NAME): TextSelector(),
                vol.Required(CONF_VALUE_PATH): self._value_selector(),
                vol.Required(SECTION_OPTIONS): section(
                    vol.Schema(
                        {
                            vol.Optional(CONF_DEVICE_CLASS): _select(
                                sorted(item.value for item in SensorDeviceClass)
                            ),
                            vol.Optional(CONF_UNIT_OF_MEASUREMENT): TextSelector(),
                            vol.Optional(CONF_STATE_CLASS): _select(
                                [item.value for item in SensorStateClass], sort=False
                            ),
                            vol.Optional(CONF_ICON): IconSelector(),
                            vol.Optional(CONF_ATTRIBUTES, default=""): _MULTILINE,
                        }
                    ),
                    {"collapsed": True},
                ),
            }
        )


class BinarySensorSubentryFlowHandler(HTTPAgentSubentryFlow):
    """Add or reconfigure a binary sensor."""

    def schema(self) -> vol.Schema:
        """Return the binary sensor form schema."""
        return vol.Schema(
            {
                vol.Required(CONF_NAME): TextSelector(),
                vol.Required(CONF_VALUE_PATH): self._value_selector(),
                vol.Required(SECTION_OPTIONS): section(
                    vol.Schema(
                        {
                            vol.Optional(CONF_DEVICE_CLASS): _select(
                                sorted(item.value for item in BinarySensorDeviceClass)
                            ),
                            vol.Optional(CONF_PAYLOAD_ON, default=""): TextSelector(),
                            vol.Optional(CONF_PAYLOAD_OFF, default=""): TextSelector(),
                            vol.Optional(CONF_ICON): IconSelector(),
                            vol.Optional(CONF_ATTRIBUTES, default=""): _MULTILINE,
                        }
                    ),
                    {"collapsed": True},
                ),
            }
        )


class DeviceTrackerSubentryFlowHandler(HTTPAgentSubentryFlow):
    """Add or reconfigure a device tracker."""

    def schema(self) -> vol.Schema:
        """Return the device tracker form schema."""
        return vol.Schema(
            {
                vol.Required(CONF_NAME): TextSelector(),
                vol.Required(CONF_LATITUDE_PATH): self._value_selector(),
                vol.Required(CONF_LONGITUDE_PATH): self._value_selector(),
                vol.Required(SECTION_OPTIONS): section(
                    vol.Schema(
                        {
                            vol.Optional(
                                CONF_GPS_ACCURACY_PATH
                            ): self._value_selector(),
                            vol.Optional(CONF_SOURCE_TYPE, default="gps"): _select(
                                SOURCE_TYPES, sort=False
                            ),
                            vol.Optional(CONF_ICON): IconSelector(),
                            vol.Optional(CONF_ATTRIBUTES, default=""): _MULTILINE,
                        }
                    ),
                    {"collapsed": True},
                ),
            }
        )
