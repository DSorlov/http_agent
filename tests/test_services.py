"""Tests for the http_agent.request action."""

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.http_agent.const import (
    ATTR_CONFIG_ENTRY_ID,
    ATTR_SELECT,
    AUTH_BEARER,
    CONF_AUTH_TYPE,
    CONF_RETRIES,
    DOMAIN,
    SERVICE_REQUEST,
)
from homeassistant.const import CONF_HEADERS, CONF_METHOD, CONF_PAYLOAD, CONF_TOKEN
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from .conftest import JSON_BODY, TEST_URL, XML_BODY


async def _entry(
    hass: HomeAssistant, config_data: dict, aioclient_mock: AiohttpClientMocker
) -> MockConfigEntry:
    """Return a loaded config entry to inherit settings from."""
    aioclient_mock.get(TEST_URL, json=JSON_BODY)
    entry = MockConfigEntry(
        domain=DOMAIN, title="Test endpoint", data=config_data, version=2
    )
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    return entry


async def _call(hass: HomeAssistant, **data):
    """Call the action and return its response."""
    return await hass.services.async_call(
        DOMAIN, SERVICE_REQUEST, data, blocking=True, return_response=True
    )


async def test_standalone_get(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """The action works without referencing a configured endpoint."""
    await _entry(hass, config_data, aioclient_mock)
    aioclient_mock.get("http://other.local/api", json=JSON_BODY)

    response = await _call(hass, url="http://other.local/api")

    assert response["status"] == 200
    assert response["format"] == "json"
    assert response["content"] == JSON_BODY
    assert response["values"] == {}


async def test_select_normalises_values(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Selected paths are extracted just like sensor values."""
    entry = await _entry(hass, config_data, aioclient_mock)

    response = await _call(
        hass,
        config_entry_id=entry.entry_id,
        select={
            "temperature": "current.temperature",
            "raining": "current.is_raining",
            "missing": "nope.nope",
        },
    )

    assert response["values"] == {
        "temperature": 21.5,
        "raining": False,
        "missing": None,
    }


async def test_select_works_for_xml(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """The same path syntax as the sensors applies to XML."""
    await _entry(hass, config_data, aioclient_mock)
    aioclient_mock.get(
        "http://other.local/xml", text=XML_BODY, headers={"content-type": "text/xml"}
    )

    response = await _call(
        hass,
        url="http://other.local/xml",
        select={"temp": "./current/temperature", "unit": "./current/temperature/@unit"},
    )

    assert response["format"] == "xml"
    assert response["values"] == {"temp": "21.5", "unit": "C"}


async def test_post_with_payload_inherits_auth(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """A POST reuses the endpoint credentials but sends its own body."""
    data = {**config_data, CONF_AUTH_TYPE: AUTH_BEARER, CONF_TOKEN: "s3cret"}
    entry = await _entry(hass, data, aioclient_mock)
    aioclient_mock.post(TEST_URL, json={"ok": True})

    response = await _call(
        hass,
        config_entry_id=entry.entry_id,
        method="POST",
        payload='{"state": "on"}',
    )

    assert response["status"] == 200
    post = aioclient_mock.mock_calls[-1]
    assert post[0] == "POST"
    assert post[2] == b'{"state": "on"}'
    assert post[3]["Authorization"] == "Bearer s3cret"


async def test_relative_url_resolves_against_the_endpoint(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """A path-only URL keeps the host of the referenced endpoint."""
    entry = await _entry(hass, config_data, aioclient_mock)
    aioclient_mock.get("http://test.local/other", json={"ok": True})

    response = await _call(hass, config_entry_id=entry.entry_id, url="/other")

    assert response["status"] == 200
    assert str(aioclient_mock.mock_calls[-1][1]) == "http://test.local/other"


async def test_headers_merge_over_the_endpoint(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Call headers are added on top of the endpoint headers."""
    data = {**config_data, CONF_HEADERS: {"Accept": "application/json", "X-A": "1"}}
    entry = await _entry(hass, data, aioclient_mock)

    await _call(
        hass,
        config_entry_id=entry.entry_id,
        headers={"X-A": "2", "X-B": "3"},
    )

    sent = aioclient_mock.mock_calls[-1][3]
    assert sent["Accept"] == "application/json"
    assert sent["X-A"] == "2"
    assert sent["X-B"] == "3"


async def test_endpoint_payload_is_not_inherited(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """What gets sent is decided by the call, not by the stored endpoint."""
    data = {**config_data, CONF_METHOD: "POST", CONF_PAYLOAD: '{"stored": true}'}
    aioclient_mock.post(TEST_URL, json=JSON_BODY)
    entry = MockConfigEntry(domain=DOMAIN, title="Test endpoint", data=data, version=2)
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()

    aioclient_mock.clear_requests()
    aioclient_mock.get(TEST_URL, json={"ok": True})

    await _call(hass, config_entry_id=entry.entry_id)

    assert aioclient_mock.mock_calls[-1][0] == "GET"
    assert aioclient_mock.mock_calls[-1][2] is None


async def test_empty_body_is_accepted(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """A fire-and-forget POST that answers 204 is not an error."""
    entry = await _entry(hass, config_data, aioclient_mock)
    aioclient_mock.post(TEST_URL, status=204, text="")

    response = await _call(hass, config_entry_id=entry.entry_id, method="POST")

    assert response["status"] == 204
    assert response["content"] == ""


async def test_credentials_are_redacted_from_the_response(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Returned headers must not leak a session cookie."""
    await _entry(hass, config_data, aioclient_mock)
    aioclient_mock.get(
        "http://other.local/api",
        json={"ok": True},
        headers={"set-cookie": "session=secret"},
    )

    response = await _call(hass, url="http://other.local/api")

    assert response["headers"]["set-cookie"] == "**REDACTED**"


async def test_without_url_or_endpoint(hass: HomeAssistant, config_data: dict) -> None:
    """One of the two must be given."""
    with pytest.raises(ServiceValidationError):
        await _call(hass, method="GET")


async def test_unknown_endpoint(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """A stale entry id is reported as a validation error."""
    await _entry(hass, config_data, aioclient_mock)

    with pytest.raises(ServiceValidationError):
        await _call(hass, config_entry_id="does-not-exist")


async def test_request_failure_raises(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Transport and status errors surface to the automation."""
    await _entry(hass, config_data, aioclient_mock)
    aioclient_mock.get("http://other.local/api", status=500)

    with pytest.raises(HomeAssistantError):
        await _call(hass, url="http://other.local/api", retries=0)


async def test_invalid_auth_raises(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """A 401 is reported rather than silently returned."""
    await _entry(hass, config_data, aioclient_mock)
    aioclient_mock.get("http://other.local/api", status=401)

    with pytest.raises(HomeAssistantError):
        await _call(hass, url="http://other.local/api")


async def test_call_overrides_endpoint_retries(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Retries can be tuned per call without touching the endpoint."""
    entry = await _entry(hass, {**config_data, CONF_RETRIES: 5}, aioclient_mock)
    aioclient_mock.clear_requests()
    aioclient_mock.get(TEST_URL, status=500)

    with pytest.raises(HomeAssistantError):
        await _call(hass, config_entry_id=entry.entry_id, retries=0)

    assert len(aioclient_mock.mock_calls) == 1


async def test_response_is_optional(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """The action can also be called without asking for a response."""
    entry = await _entry(hass, config_data, aioclient_mock)

    result = await hass.services.async_call(
        DOMAIN,
        SERVICE_REQUEST,
        {
            ATTR_CONFIG_ENTRY_ID: entry.entry_id,
            ATTR_SELECT: {"t": "current.temperature"},
        },
        blocking=True,
    )

    assert result is None
