"""Tests for setup, migration and the entity platforms."""

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.http_agent.const import (
    CONF_LATITUDE_PATH,
    CONF_LONGITUDE_PATH,
    CONF_VALUE_PATH,
    CONFIG_VERSION,
    DOMAIN,
    SUBENTRY_TYPE_BINARY_SENSOR,
    SUBENTRY_TYPE_DEVICE_TRACKER,
    SUBENTRY_TYPE_SENSOR,
)
from homeassistant.config_entries import ConfigEntryState, ConfigSubentryData
from homeassistant.const import (
    CONF_HEADERS,
    CONF_METHOD,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_UNIT_OF_MEASUREMENT,
    CONF_URL,
    STATE_OFF,
    STATE_ON,
)
from homeassistant.core import HomeAssistant

from .conftest import JSON_BODY, TEST_URL

SUBENTRIES = [
    ConfigSubentryData(
        data={
            CONF_NAME: "Temperature",
            CONF_VALUE_PATH: "current.temperature",
            "device_class": "temperature",
            CONF_UNIT_OF_MEASUREMENT: "°C",
            "state_class": "measurement",
            "attributes": {"humidity": "current.humidity"},
        },
        subentry_type=SUBENTRY_TYPE_SENSOR,
        title="Temperature",
        unique_id=None,
    ),
    ConfigSubentryData(
        data={CONF_NAME: "Raining", CONF_VALUE_PATH: "current.is_raining"},
        subentry_type=SUBENTRY_TYPE_BINARY_SENSOR,
        title="Raining",
        unique_id=None,
    ),
]


async def _setup(
    hass: HomeAssistant, config_data: dict, subentries=SUBENTRIES
) -> MockConfigEntry:
    """Add and set up a config entry."""
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Test endpoint",
        data=config_data,
        version=CONFIG_VERSION,
        subentries_data=subentries,
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def test_setup_creates_entities(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Each subentry becomes exactly one entity."""
    aioclient_mock.get(TEST_URL, json=JSON_BODY)

    entry = await _setup(hass, config_data)
    assert entry.state is ConfigEntryState.LOADED

    state = hass.states.get("sensor.temperature")
    assert state is not None
    assert state.state == "21.5"
    assert state.attributes[CONF_UNIT_OF_MEASUREMENT] == "°C"
    assert state.attributes["device_class"] == "temperature"
    assert state.attributes["humidity"] == 48

    assert hass.states.get("binary_sensor.raining").state == STATE_OFF


async def test_binary_sensor_truthy_string(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Common on/off spellings are recognised."""
    aioclient_mock.get(TEST_URL, json={"status": "ONLINE"})

    await _setup(
        hass,
        config_data,
        [
            ConfigSubentryData(
                data={CONF_NAME: "Online", CONF_VALUE_PATH: "status"},
                subentry_type=SUBENTRY_TYPE_BINARY_SENSOR,
                title="Online",
                unique_id=None,
            )
        ],
    )

    assert hass.states.get("binary_sensor.online").state == STATE_ON


async def test_device_tracker(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Coordinates are read from two separate paths."""
    aioclient_mock.get(TEST_URL, json={"pos": {"lat": 59.33, "lon": 18.06}})

    await _setup(
        hass,
        config_data,
        [
            ConfigSubentryData(
                data={
                    CONF_NAME: "Car",
                    CONF_LATITUDE_PATH: "pos.lat",
                    CONF_LONGITUDE_PATH: "pos.lon",
                },
                subentry_type=SUBENTRY_TYPE_DEVICE_TRACKER,
                title="Car",
                unique_id=None,
            )
        ],
    )

    state = hass.states.get("device_tracker.car")
    assert state is not None
    assert state.attributes["latitude"] == 59.33
    assert state.attributes["longitude"] == 18.06


async def test_missing_path_yields_unknown(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """An unresolvable path leaves the entity unknown rather than failing setup."""
    aioclient_mock.get(TEST_URL, json={"other": 1})

    await _setup(
        hass,
        config_data,
        [
            ConfigSubentryData(
                data={CONF_NAME: "Gone", CONF_VALUE_PATH: "does.not.exist"},
                subentry_type=SUBENTRY_TYPE_SENSOR,
                title="Gone",
                unique_id=None,
            )
        ],
    )

    assert hass.states.get("sensor.gone").state == "unknown"


async def test_setup_retries_when_endpoint_is_down(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """A dead endpoint results in a retry rather than a hard failure."""
    aioclient_mock.get(TEST_URL, exc=TimeoutError)

    entry = await _setup(hass, config_data)

    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_unload(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Unloading removes the entities again."""
    aioclient_mock.get(TEST_URL, json=JSON_BODY)

    entry = await _setup(hass, config_data)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.state is ConfigEntryState.NOT_LOADED


async def test_migration_from_version_1(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Legacy sensor lists become subentries."""
    aioclient_mock.get(TEST_URL, json=JSON_BODY)

    entry = MockConfigEntry(
        domain=DOMAIN,
        title="HTTP Agent - test.local",
        version=1,
        data={
            CONF_URL: TEST_URL,
            CONF_METHOD: "GET",
            "interval": 30,
            CONF_HEADERS: [{"key": "Accept", "value": "application/json"}],
            "sensors": [
                {
                    "sensor_name": "Temperature",
                    "sensor_type": "sensor",
                    "sensor_state": "current.temperature",
                    "sensor_device_class": "temperature",
                    "sensor_unit": "°C",
                    "sensor_color": "current.humidity",
                },
                {
                    "sensor_name": "Legacy number",
                    "sensor_type": "number",
                    "sensor_state": "current.humidity",
                },
                {
                    "sensor_name": "Raining",
                    "sensor_type": "binary_sensor",
                    "sensor_state": "current.is_raining",
                    "sensor_device_class": "none",
                },
            ],
        },
    )
    entry.add_to_hass(hass)

    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    assert entry.version == CONFIG_VERSION
    assert entry.data[CONF_HEADERS] == {"Accept": "application/json"}
    assert entry.data[CONF_SCAN_INTERVAL] == 30

    subentries = list(entry.subentries.values())
    assert len(subentries) == 3
    assert [sub.subentry_type for sub in subentries] == [
        SUBENTRY_TYPE_SENSOR,
        SUBENTRY_TYPE_SENSOR,
        SUBENTRY_TYPE_BINARY_SENSOR,
    ]
    assert subentries[0].data[CONF_VALUE_PATH] == "current.temperature"
    assert subentries[0].data["attributes"] == {"color": "current.humidity"}
    assert "device_class" not in subentries[2].data

    assert hass.states.get("sensor.temperature") is not None
