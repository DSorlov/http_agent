"""Tests for the subentry flows, reconfigure, reauth and diagnostics."""

from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.http_agent.config_flow import SECTION_ADVANCED, SECTION_OPTIONS
from custom_components.http_agent.const import (
    AUTH_BEARER,
    AUTH_NONE,
    CONF_AUTH_TYPE,
    CONF_LATITUDE_PATH,
    CONF_LONGITUDE_PATH,
    CONF_VALUE_PATH,
    DOMAIN,
    SUBENTRY_TYPE_BINARY_SENSOR,
    SUBENTRY_TYPE_DEVICE_TRACKER,
    SUBENTRY_TYPE_SENSOR,
)
from custom_components.http_agent.diagnostics import async_get_config_entry_diagnostics
from homeassistant.components.diagnostics import REDACTED
from homeassistant.config_entries import SOURCE_USER, ConfigEntryState
from homeassistant.const import CONF_METHOD, CONF_NAME, CONF_TOKEN, CONF_URL
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import JSON_BODY, TEST_URL


async def _loaded_entry(
    hass: HomeAssistant, config_data: dict, aioclient_mock: AiohttpClientMocker
) -> MockConfigEntry:
    """Return a set up config entry with no subentries yet."""
    aioclient_mock.get(TEST_URL, json=JSON_BODY)
    entry = MockConfigEntry(
        domain=DOMAIN, title="Test endpoint", data=config_data, version=2
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.LOADED
    return entry


async def test_add_sensor_subentry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """A sensor can be added from the discovered values."""
    entry = await _loaded_entry(hass, config_data, aioclient_mock)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_SENSOR), context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    options = result["data_schema"].schema[CONF_VALUE_PATH].config["options"]
    assert any(option["value"] == "current.temperature" for option in options)

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Temperature",
            CONF_VALUE_PATH: "current.temperature",
            SECTION_OPTIONS: {
                "device_class": "temperature",
                "unit_of_measurement": "°C",
                "attributes": "humidity: current.humidity",
            },
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    subentry = next(iter(entry.subentries.values()))
    assert subentry.subentry_type == SUBENTRY_TYPE_SENSOR
    assert subentry.data["attributes"] == {"humidity": "current.humidity"}

    state = hass.states.get("sensor.temperature")
    assert state.state == "21.5"
    assert state.attributes["humidity"] == 48


async def test_add_binary_sensor_subentry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """A binary sensor can be added with explicit payloads."""
    entry = await _loaded_entry(hass, config_data, aioclient_mock)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_BINARY_SENSOR), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Raining",
            CONF_VALUE_PATH: "current.is_raining",
            SECTION_OPTIONS: {"device_class": "moisture"},
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert hass.states.get("binary_sensor.raining").state == "off"


async def test_add_device_tracker_subentry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """A device tracker needs two paths."""
    aioclient_mock.get(TEST_URL, json={"lat": 59.33, "lon": 18.06})
    entry = MockConfigEntry(
        domain=DOMAIN, title="Test endpoint", data=config_data, version=2
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_DEVICE_TRACKER), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Car",
            CONF_LATITUDE_PATH: "lat",
            CONF_LONGITUDE_PATH: "lon",
            SECTION_OPTIONS: {"source_type": "gps"},
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert hass.states.get("device_tracker.car").attributes["latitude"] == 59.33


async def test_subentry_rejects_malformed_attributes(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Attribute lines without a colon produce a form error."""
    entry = await _loaded_entry(hass, config_data, aioclient_mock)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_SENSOR), context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Temperature",
            CONF_VALUE_PATH: "current.temperature",
            SECTION_OPTIONS: {"attributes": "nonsense"},
        },
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_attributes"}


async def test_reconfigure_subentry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """An existing subentry can be pointed at another value."""
    entry = await _loaded_entry(hass, config_data, aioclient_mock)

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_SENSOR), context={"source": SOURCE_USER}
    )
    await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Temperature",
            CONF_VALUE_PATH: "current.temperature",
            SECTION_OPTIONS: {},
        },
    )
    await hass.async_block_till_done()
    subentry_id = next(iter(entry.subentries))

    result = await hass.config_entries.subentries.async_init(
        (entry.entry_id, SUBENTRY_TYPE_SENSOR),
        context={"source": "reconfigure", "subentry_id": subentry_id},
    )
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.subentries.async_configure(
        result["flow_id"],
        {
            CONF_NAME: "Humidity",
            CONF_VALUE_PATH: "current.humidity",
            SECTION_OPTIONS: {},
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert entry.subentries[subentry_id].data[CONF_VALUE_PATH] == "current.humidity"


async def test_reconfigure_entry(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """The endpoint can be changed without recreating the entry."""
    entry = await _loaded_entry(hass, config_data, aioclient_mock)
    aioclient_mock.get("http://other.local/api", json=JSON_BODY)

    result = await entry.start_reconfigure_flow(hass)
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_URL: "http://other.local/api",
            CONF_METHOD: "GET",
            CONF_AUTH_TYPE: AUTH_NONE,
            CONF_NAME: "Other endpoint",
            SECTION_ADVANCED: {},
        },
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert entry.data[CONF_URL] == "http://other.local/api"
    assert len(hass.config_entries.async_entries(DOMAIN)) == 1


async def test_reauth_flow(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """A 401 during polling starts reauth and new credentials are stored."""
    data = {**config_data, CONF_AUTH_TYPE: AUTH_BEARER, CONF_TOKEN: "old"}
    aioclient_mock.get(TEST_URL, status=401)

    entry = MockConfigEntry(domain=DOMAIN, title="Test endpoint", data=data, version=2)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    flows = [
        flow
        for flow in hass.config_entries.flow.async_progress()
        if flow["context"]["source"] == "reauth"
    ]
    assert len(flows) == 1

    aioclient_mock.clear_requests()
    aioclient_mock.get(TEST_URL, json=JSON_BODY)

    result = await hass.config_entries.flow.async_configure(
        flows[0]["flow_id"], {CONF_TOKEN: "new"}
    )
    await hass.async_block_till_done()

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert entry.data[CONF_TOKEN] == "new"


async def test_diagnostics_redacts_credentials(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Diagnostics must never leak the URL or credentials."""
    data = {**config_data, CONF_AUTH_TYPE: AUTH_BEARER, CONF_TOKEN: "s3cret"}
    aioclient_mock.get(TEST_URL, json=JSON_BODY)

    entry = MockConfigEntry(domain=DOMAIN, title="Test endpoint", data=data, version=2)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    diagnostics = await async_get_config_entry_diagnostics(hass, entry)

    assert diagnostics["entry"][CONF_TOKEN] == REDACTED
    assert diagnostics["entry"][CONF_URL] == REDACTED
    assert diagnostics["request_headers"]["Authorization"] == "**REDACTED**"
    assert diagnostics["response"]["status"] == 200
    assert "s3cret" not in str(diagnostics)
