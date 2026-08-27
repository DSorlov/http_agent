"""Tests for value discovery and entity type guessing."""

from custom_components.http_agent.const import (
    SUBENTRY_TYPE_BINARY_SENSOR,
    SUBENTRY_TYPE_SENSOR,
)
from custom_components.http_agent.discovery import DiscoveredValue, discover_values
from custom_components.http_agent.parser import ParsedResponse

from .conftest import HTML_BODY, JSON_BODY, XML_BODY


def test_discover_json_paths():
    response = ParsedResponse.parse(
        __import__("json").dumps(JSON_BODY), 200, {"content-type": "application/json"}
    )
    paths = {value.path for value in discover_values(response)}
    assert "current.temperature" in paths
    assert "current.is_raining" in paths
    assert "readings[1].value" in paths


def test_discovered_paths_resolve_back_to_values():
    """Every discovered path must be usable as an extraction path."""
    for body, headers in (
        (__import__("json").dumps(JSON_BODY), {"content-type": "application/json"}),
        (XML_BODY, {"content-type": "text/xml"}),
        (HTML_BODY, {"content-type": "text/html"}),
    ):
        response = ParsedResponse.parse(body, 200, headers)
        found = discover_values(response)
        assert found
        for value in found:
            assert response.extract(value.path) is not None, value.path


def test_discover_xml_paths_include_attributes():
    response = ParsedResponse.parse(XML_BODY, 200, {"content-type": "text/xml"})
    paths = {value.path for value in discover_values(response)}
    assert "./current/temperature" in paths
    assert "./current/temperature/@unit" in paths
    assert "./sensor[2]" in paths


def test_guess_sensor_from_temperature():
    value = DiscoveredValue(path="current.temperature", value=21.5)
    assert value.suggested_platform == SUBENTRY_TYPE_SENSOR
    assert value.suggested_device_class == "temperature"
    assert value.suggested_unit == "°C"
    assert value.suggested_state_class == "measurement"
    assert value.name == "Temperature"


def test_guess_binary_sensor_from_bool():
    value = DiscoveredValue(path="current.is_raining", value=False)
    assert value.suggested_platform == SUBENTRY_TYPE_BINARY_SENSOR
    assert value.suggested_state_class is None


def test_guess_energy_is_total_increasing():
    value = DiscoveredValue(path="meter.energy", value=1234)
    assert value.suggested_state_class == "total_increasing"


def test_plain_string_is_a_sensor_without_device_class():
    value = DiscoveredValue(path="name", value="Weather station")
    assert value.suggested_platform == SUBENTRY_TYPE_SENSOR
    assert value.suggested_device_class is None
    assert value.suggested_unit is None


def test_preview_is_truncated():
    value = DiscoveredValue(path="blob", value="x" * 200)
    assert len(value.preview) == 60
    assert value.preview.endswith("…")
