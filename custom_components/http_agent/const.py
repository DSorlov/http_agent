"""Constants for the HTTP Agent integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "http_agent"

MANUFACTURER: Final = "HTTP Agent"

# Config entry schema version. Version 1 was the pre-subentry layout.
CONFIG_VERSION: Final = 2
CONFIG_MINOR_VERSION: Final = 1

# --- Config entry keys (integration specific, core keys are imported directly) ---
CONF_AUTH_TYPE: Final = "auth_type"
CONF_API_KEY_HEADER: Final = "api_key_header"
CONF_CONTENT_TYPE: Final = "content_type"
CONF_RESPONSE_FORMAT: Final = "response_format"
CONF_FOLLOW_REDIRECTS: Final = "follow_redirects"
CONF_RETRIES: Final = "retries"

# --- Subentry (entity) keys ---
CONF_VALUE_PATH: Final = "value_path"
CONF_ATTRIBUTES: Final = "attributes"
CONF_STATE_CLASS: Final = "state_class"
CONF_PAYLOAD_ON: Final = "payload_on"
CONF_PAYLOAD_OFF: Final = "payload_off"
CONF_LATITUDE_PATH: Final = "latitude_path"
CONF_LONGITUDE_PATH: Final = "longitude_path"
CONF_GPS_ACCURACY_PATH: Final = "gps_accuracy_path"
CONF_SOURCE_TYPE: Final = "source_type"

# Internal key used by the config flow to hand picked values to the entry creation.
CONF_SELECTED_VALUES: Final = "selected_values"

# --- Subentry types (one per supported platform) ---
SUBENTRY_TYPE_SENSOR: Final = "sensor"
SUBENTRY_TYPE_BINARY_SENSOR: Final = "binary_sensor"
SUBENTRY_TYPE_DEVICE_TRACKER: Final = "device_tracker"

# --- Defaults ---
DEFAULT_METHOD: Final = "GET"
DEFAULT_TIMEOUT: Final = 10
DEFAULT_SCAN_INTERVAL: Final = 60
DEFAULT_VERIFY_SSL: Final = True
DEFAULT_FOLLOW_REDIRECTS: Final = True
DEFAULT_RETRIES: Final = 0
DEFAULT_CONTENT_TYPE: Final = "application/json"
DEFAULT_API_KEY_HEADER: Final = "X-API-Key"

MIN_TIMEOUT: Final = 1
MAX_TIMEOUT: Final = 300
MIN_SCAN_INTERVAL: Final = 5
MAX_SCAN_INTERVAL: Final = 86400
MAX_RETRIES: Final = 10

# Seconds to wait between two attempts of the same poll.
RETRY_DELAY: Final = 1

# Guard rails for the value discovery step so huge payloads cannot blow up the UI.
MAX_DISCOVERED_VALUES: Final = 250
MAX_DISCOVERY_DEPTH: Final = 8
MAX_PREVIEW_LENGTH: Final = 1500

# --- HTTP methods ---
METHOD_GET: Final = "GET"
METHOD_POST: Final = "POST"
METHOD_PUT: Final = "PUT"
METHOD_PATCH: Final = "PATCH"
METHOD_DELETE: Final = "DELETE"
METHOD_HEAD: Final = "HEAD"

HTTP_METHODS: Final = [
    METHOD_GET,
    METHOD_POST,
    METHOD_PUT,
    METHOD_PATCH,
    METHOD_DELETE,
    METHOD_HEAD,
]

METHODS_WITH_BODY: Final = {METHOD_POST, METHOD_PUT, METHOD_PATCH, METHOD_DELETE}

CONTENT_TYPES: Final = [
    "application/json",
    "application/xml",
    "application/x-www-form-urlencoded",
    "text/plain",
    "text/xml",
]

# --- Authentication presets ---
AUTH_NONE: Final = "none"
AUTH_BEARER: Final = "bearer"
AUTH_API_KEY: Final = "api_key"
AUTH_BASIC: Final = "basic"

AUTH_TYPES: Final = [AUTH_NONE, AUTH_BEARER, AUTH_API_KEY, AUTH_BASIC]

# --- Response formats ---
FORMAT_AUTO: Final = "auto"
FORMAT_JSON: Final = "json"
FORMAT_XML: Final = "xml"
FORMAT_HTML: Final = "html"
FORMAT_TEXT: Final = "text"

RESPONSE_FORMATS: Final = [
    FORMAT_AUTO,
    FORMAT_JSON,
    FORMAT_XML,
    FORMAT_HTML,
    FORMAT_TEXT,
]

# --- Device tracker source types ---
SOURCE_TYPES: Final = ["gps", "router", "bluetooth", "bluetooth_le"]

# Values that are interpreted as "on" for binary sensors when no explicit
# payload_on/payload_off is configured.
TRUTHY_VALUES: Final = frozenset(
    {
        "1",
        "active",
        "connected",
        "detected",
        "enabled",
        "home",
        "on",
        "online",
        "open",
        "true",
        "unlocked",
        "yes",
    }
)

FALSY_VALUES: Final = frozenset(
    {
        "0",
        "closed",
        "disabled",
        "disconnected",
        "false",
        "inactive",
        "locked",
        "no",
        "not_detected",
        "not_home",
        "off",
        "offline",
    }
)
