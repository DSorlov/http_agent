"""Constants for the HTTP Agent integration."""
from typing import Final

DOMAIN: Final = "http_agent"

# Default values
DEFAULT_TIMEOUT = 10
DEFAULT_INTERVAL = 60
DEFAULT_SSL_VERIFY = True
DEFAULT_METHOD = "GET"

# Configuration keys
CONF_SENSORS = "sensors"
CONF_SSL_VERIFY = "ssl_verify"
CONF_TIMEOUT = "timeout"
CONF_INTERVAL = "interval"
CONF_METHOD = "method"
CONF_PAYLOAD = "payload"
CONF_QUERYSTRING = "querystring"
CONF_ENABLED = "enabled"

# Sensor states
STATE_OK = "ok"
STATE_ERROR = "error"
STATE_TIMEOUT = "timeout"
STATE_UNKNOWN = "unknown"

# Service schema keys
SERVICE_URL = "url"
SERVICE_METHOD = "method"
SERVICE_PAYLOAD = "payload"
SERVICE_HEADERS = "headers"
SERVICE_TIMEOUT = "timeout"
SERVICE_SSL_VERIFY = "ssl_verify"
SERVICE_QUERYSTRING = "querystring"