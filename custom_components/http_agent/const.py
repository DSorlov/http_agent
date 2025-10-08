"""Constants for the HTTP Agent integration."""

from typing import Final

DOMAIN: Final = "http_agent"

# Default values
DEFAULT_TIMEOUT = 10
DEFAULT_INTERVAL = 60
DEFAULT_METHOD = "GET"
DEFAULT_VERIFY_SSL = True

# Configuration keys
CONF_URL = "url"
CONF_METHOD = "method"
CONF_TIMEOUT = "timeout"
CONF_INTERVAL = "interval"
CONF_VERIFY_SSL = "verify_ssl"
CONF_HEADERS = "headers"
CONF_PAYLOAD = "payload"
CONF_CONTENT_TYPE = "content_type"
CONF_SENSORS = "sensors"
CONF_SENSOR_NAME = "sensor_name"
CONF_SENSOR_STATE = "sensor_state"
CONF_SENSOR_ICON = "sensor_icon"
CONF_SENSOR_COLOR = "sensor_color"

# Sensor type configuration
CONF_SENSOR_TYPE = "sensor_type"
CONF_SENSOR_DEVICE_CLASS = "sensor_device_class"
CONF_SENSOR_UNIT = "sensor_unit"

# Sensor Types
SENSOR_TYPES = {
    "sensor": "Sensor",
    "binary_sensor": "Binary Sensor",
    "number": "Number",
    "device_tracker": "Device Tracker",
}

# Sensor Device Classes by type
SENSOR_DEVICE_CLASSES = {
    "apparent_power",
    "aqi",
    "atmospheric_pressure",
    "battery",
    "carbon_dioxide",
    "carbon_monoxide",
    "current",
    "data_rate",
    "data_size",
    "date",
    "distance",
    "duration",
    "energy",
    "energy_storage",
    "enum",
    "frequency",
    "gas",
    "humidity",
    "illuminance",
    "irradiance",
    "moisture",
    "monetary",
    "nitrogen_dioxide",
    "nitrogen_monoxide",
    "nitrous_oxide",
    "ozone",
    "ph",
    "pm1",
    "pm10",
    "pm25",
    "power",
    "power_factor",
    "precipitation",
    "precipitation_intensity",
    "pressure",
    "reactive_power",
    "signal_strength",
    "sound_pressure",
    "speed",
    "sulphur_dioxide",
    "temperature",
    "timestamp",
    "volatile_organic_compounds",
    "volatile_organic_compounds_parts",
    "voltage",
    "volume",
    "volume_flow_rate",
    "volume_storage",
    "water",
    "weight",
    "wind_speed",
}

BINARY_SENSOR_DEVICE_CLASSES = {
    "battery",
    "battery_charging",
    "carbon_monoxide",
    "cold",
    "connectivity",
    "door",
    "garage_door",
    "gas",
    "heat",
    "light",
    "lock",
    "moisture",
    "motion",
    "moving",
    "occupancy",
    "opening",
    "plug",
    "power",
    "presence",
    "problem",
    "running",
    "safety",
    "smoke",
    "sound",
    "tamper",
    "update",
    "vibration",
    "window",
}

NUMBER_DEVICE_CLASSES = {
    "apparent_power",
    "aqi",
    "atmospheric_pressure",
    "battery",
    "carbon_dioxide",
    "carbon_monoxide",
    "current",
    "data_rate",
    "data_size",
    "distance",
    "duration",
    "energy",
    "energy_storage",
    "frequency",
    "gas",
    "humidity",
    "illuminance",
    "irradiance",
    "moisture",
    "monetary",
    "nitrogen_dioxide",
    "nitrogen_monoxide",
    "nitrous_oxide",
    "ozone",
    "ph",
    "pm1",
    "pm10",
    "pm25",
    "power",
    "power_factor",
    "precipitation",
    "precipitation_intensity",
    "pressure",
    "reactive_power",
    "signal_strength",
    "sound_pressure",
    "speed",
    "sulphur_dioxide",
    "temperature",
    "volatile_organic_compounds",
    "volatile_organic_compounds_parts",
    "voltage",
    "volume",
    "volume_flow_rate",
    "volume_storage",
    "water",
    "weight",
    "wind_speed",
}

# Device Tracker specific configuration
CONF_TRACKER_LATITUDE = "tracker_latitude"
CONF_TRACKER_LONGITUDE = "tracker_longitude"
CONF_TRACKER_LOCATION_NAME = "tracker_location_name"
CONF_TRACKER_SOURCE_TYPE = "tracker_source_type"

# HTTP Methods
HTTP_METHODS = [
    "GET",
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
]

# Methods that support payloads
HTTP_METHODS_WITH_PAYLOAD = [
    "POST",
    "PUT",
    "DELETE",
    "PATCH",
]

# Content Types
CONTENT_TYPES = [
    "application/json",
    "application/xml",
    "text/xml",
    "application/x-www-form-urlencoded",
    "text/plain",
]
