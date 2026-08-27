"""Tests for the HTTP Agent config and subentry flows."""

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker
import voluptuous as vol

from custom_components.http_agent.config_flow import (
    SECTION_ADVANCED,
    format_key_values,
    parse_key_values,
)
from custom_components.http_agent.const import (
    AUTH_BEARER,
    AUTH_NONE,
    CONF_AUTH_TYPE,
    CONF_SELECTED_VALUES,
    DOMAIN,
    SUBENTRY_TYPE_BINARY_SENSOR,
    SUBENTRY_TYPE_SENSOR,
)
from homeassistant.config_entries import SOURCE_USER
from homeassistant.const import (
    CONF_METHOD,
    CONF_NAME,
    CONF_PAYLOAD,
    CONF_TOKEN,
    CONF_URL,
)
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

from .conftest import JSON_BODY, TEST_URL

USER_INPUT = {
    CONF_URL: TEST_URL,
    CONF_METHOD: "GET",
    CONF_AUTH_TYPE: AUTH_NONE,
    CONF_NAME: "Test endpoint",
    SECTION_ADVANCED: {},
}


async def _start(hass: HomeAssistant, user_input: dict) -> dict:
    """Run the user step of the config flow."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return await hass.config_entries.flow.async_configure(result["flow_id"], user_input)


async def test_full_flow_creates_entry_and_subentries(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A successful test request leads straight to the value picker."""
    aioclient_mock.get(TEST_URL, json=JSON_BODY)

    result = await _start(hass, USER_INPUT)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "select_values"
    assert result["description_placeholders"]["status"] == "200"
    assert result["description_placeholders"]["format"] == "JSON"
    assert int(result["description_placeholders"]["count"]) > 0

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            CONF_SELECTED_VALUES: [
                "current.temperature",
                "current.is_raining",
            ]
        },
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Test endpoint"
    assert result["data"][CONF_URL] == TEST_URL

    entry = hass.config_entries.async_entries(DOMAIN)[0]
    kinds = {sub.subentry_type for sub in entry.subentries.values()}
    assert kinds == {SUBENTRY_TYPE_SENSOR, SUBENTRY_TYPE_BINARY_SENSOR}

    sensor = next(
        sub
        for sub in entry.subentries.values()
        if sub.subentry_type == SUBENTRY_TYPE_SENSOR
    )
    assert sensor.data["device_class"] == "temperature"
    assert sensor.data["unit_of_measurement"] == "°C"


async def test_flow_without_selecting_values(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The picker can be skipped and entities added later."""
    aioclient_mock.get(TEST_URL, json=JSON_BODY)

    result = await _start(hass, USER_INPUT)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert hass.config_entries.async_entries(DOMAIN)[0].subentries == {}


async def test_invalid_url_is_rejected(hass: HomeAssistant) -> None:
    """A relative URL never reaches the network."""
    result = await _start(hass, {**USER_INPUT, CONF_URL: "not-a-url"})

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_URL: "invalid_url"}


async def test_cannot_connect_is_shown_on_the_form(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Connection errors are reported on the step the user submitted."""
    aioclient_mock.get(TEST_URL, exc=TimeoutError)

    result = await _start(hass, USER_INPUT)

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    assert result["errors"] == {"base": "cannot_connect"}


async def test_bad_status_is_reported(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 500 response keeps the user on the form."""
    aioclient_mock.get(TEST_URL, status=500)

    result = await _start(hass, USER_INPUT)

    assert result["errors"] == {"base": "bad_status"}


async def test_bearer_auth_adds_a_credentials_step(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Picking a preset asks for credentials and sends the header."""
    aioclient_mock.get(TEST_URL, json=JSON_BODY)

    result = await _start(hass, {**USER_INPUT, CONF_AUTH_TYPE: AUTH_BEARER})
    assert result["step_id"] == "credentials"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: "s3cret"}
    )
    assert result["step_id"] == "select_values"
    assert aioclient_mock.mock_calls[0][3]["Authorization"] == "Bearer s3cret"


async def test_invalid_auth_returns_to_credentials(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """A 401 sends the user back to the credentials form."""
    aioclient_mock.get(TEST_URL, status=401)

    result = await _start(hass, {**USER_INPUT, CONF_AUTH_TYPE: AUTH_BEARER})
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_TOKEN: "wrong"}
    )

    assert result["step_id"] == "credentials"
    assert result["errors"] == {"base": "invalid_auth"}


async def test_post_adds_a_body_step(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """Methods that carry a body get an extra step."""
    aioclient_mock.post(TEST_URL, json=JSON_BODY)

    result = await _start(hass, {**USER_INPUT, CONF_METHOD: "POST"})
    assert result["step_id"] == "body"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {"content_type": "application/json", CONF_PAYLOAD: '{"q": 1}'},
    )
    assert result["step_id"] == "select_values"


async def test_extra_headers_are_parsed(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker
) -> None:
    """The multiline header field becomes a header dictionary."""
    aioclient_mock.get(TEST_URL, json=JSON_BODY)

    result = await _start(
        hass,
        {
            **USER_INPUT,
            SECTION_ADVANCED: {"extra_headers": "Accept: application/json\nX-Foo: bar"},
        },
    )
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {})

    assert result["data"]["headers"] == {
        "Accept": "application/json",
        "X-Foo": "bar",
    }


async def test_malformed_headers_are_rejected(hass: HomeAssistant) -> None:
    """Header lines without a colon produce a form error."""
    result = await _start(
        hass, {**USER_INPUT, SECTION_ADVANCED: {"extra_headers": "nonsense"}}
    )

    assert result["errors"] == {"base": "invalid_headers"}


async def test_duplicate_endpoint_is_aborted(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, mock_entry
) -> None:
    """The same URL and method cannot be configured twice."""
    aioclient_mock.get(TEST_URL, json=JSON_BODY)
    mock_entry.add_to_hass(hass)

    result = await _start(hass, USER_INPUT)

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("A: 1\nB: 2", {"A": "1", "B": "2"}),
        ("  A :  1  ", {"A": "1"}),
        ("# comment\nA: 1", {"A": "1"}),
        ("A: http://x/y", {"A": "http://x/y"}),
        ("", {}),
    ],
)
def test_parse_key_values(text, expected):
    assert parse_key_values(text) == expected


@pytest.mark.parametrize("text", ["nocolon", ": missing name"])
def test_parse_key_values_rejects_bad_lines(text):
    with pytest.raises(vol.Invalid):
        parse_key_values(text)


def test_format_key_values_round_trip():
    values = {"A": "1", "B": "2"}
    assert parse_key_values(format_key_values(values)) == values
