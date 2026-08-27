"""Tests for entity value coercion."""

from datetime import UTC, datetime

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.http_agent.binary_sensor import _as_bool
from custom_components.http_agent.const import (
    CONF_PAYLOAD_OFF,
    CONF_PAYLOAD_ON,
    CONF_STATE_CLASS,
    CONF_VALUE_PATH,
    SUBENTRY_TYPE_BINARY_SENSOR,
    SUBENTRY_TYPE_SENSOR,
)
from custom_components.http_agent.sensor import _as_datetime, _as_float
from homeassistant.components.sensor import SensorDeviceClass
from homeassistant.config_entries import ConfigSubentryData
from homeassistant.const import CONF_DEVICE_CLASS, CONF_NAME, STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from .conftest import TEST_URL
from .test_init import _setup


@pytest.mark.parametrize(
    ("value", "payload_on", "payload_off", "expected"),
    [
        (True, None, None, True),
        (False, None, None, False),
        ("on", None, None, True),
        ("OFF", None, None, False),
        ("Open", None, None, True),
        (1, None, None, True),
        (0, None, None, False),
        ("", None, None, False),
        (None, None, None, None),
        ("weird", None, None, None),
        ("RUNNING", "RUNNING", "STOPPED", True),
        ("STOPPED", "RUNNING", "STOPPED", False),
        ("other", "RUNNING", "STOPPED", None),
        ("other", "RUNNING", None, False),
        ("other", None, "STOPPED", True),
    ],
)
def test_as_bool(value, payload_on, payload_off, expected):
    assert _as_bool(value, payload_on, payload_off) is expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [("21.5", 21.5), ("21,5", 21.5), (" 3 ", 3.0), (True, 1.0), ("abc", None)],
)
def test_as_float(value, expected):
    assert _as_float(value) == expected


def test_as_datetime_from_iso_string():
    parsed = _as_datetime("2026-01-02T03:04:05+00:00", SensorDeviceClass.TIMESTAMP)
    assert parsed == datetime(2026, 1, 2, 3, 4, 5, tzinfo=UTC)


def test_as_datetime_from_epoch():
    parsed = _as_datetime(0, SensorDeviceClass.TIMESTAMP)
    assert parsed == datetime(1970, 1, 1, tzinfo=UTC)


def test_as_datetime_invalid():
    assert _as_datetime("nope", SensorDeviceClass.TIMESTAMP) is None


async def test_unsupported_device_class_is_ignored(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """A device class that no longer exists must not break the entity."""
    aioclient_mock.get(TEST_URL, json={"value": "hello"})

    await _setup(
        hass,
        config_data,
        [
            ConfigSubentryData(
                data={
                    CONF_NAME: "Odd",
                    CONF_VALUE_PATH: "value",
                    CONF_DEVICE_CLASS: "not_a_device_class",
                },
                subentry_type=SUBENTRY_TYPE_SENSOR,
                title="Odd",
                unique_id=None,
            )
        ],
    )

    state = hass.states.get("sensor.odd")
    assert state.state == "hello"
    assert "device_class" not in state.attributes


async def test_non_numeric_value_with_state_class_is_unknown(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Numeric sensors report unknown rather than a bogus state."""
    aioclient_mock.get(TEST_URL, json={"value": "n/a"})

    await _setup(
        hass,
        config_data,
        [
            ConfigSubentryData(
                data={
                    CONF_NAME: "Broken",
                    CONF_VALUE_PATH: "value",
                    CONF_STATE_CLASS: "measurement",
                },
                subentry_type=SUBENTRY_TYPE_SENSOR,
                title="Broken",
                unique_id=None,
            )
        ],
    )

    assert hass.states.get("sensor.broken").state == STATE_UNKNOWN


async def test_binary_sensor_payload_mapping(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Explicit payloads win over the built-in truthy words."""
    aioclient_mock.get(TEST_URL, json={"mode": "ARMED"})

    await _setup(
        hass,
        config_data,
        [
            ConfigSubentryData(
                data={
                    CONF_NAME: "Armed",
                    CONF_VALUE_PATH: "mode",
                    CONF_PAYLOAD_ON: "ARMED",
                    CONF_PAYLOAD_OFF: "DISARMED",
                },
                subentry_type=SUBENTRY_TYPE_BINARY_SENSOR,
                title="Armed",
                unique_id=None,
            )
        ],
    )

    assert hass.states.get("binary_sensor.armed").state == "on"
