"""Tests for the HTTP client layer."""

from unittest.mock import AsyncMock, patch

import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.http_agent.api import (
    CannotConnect,
    EmptyResponse,
    InvalidAuth,
    InvalidResponse,
    async_request,
    build_request_headers,
    redact_headers,
)
from custom_components.http_agent.const import (
    AUTH_API_KEY,
    AUTH_BEARER,
    CONF_API_KEY_HEADER,
    CONF_AUTH_TYPE,
    CONF_RETRIES,
)
from custom_components.http_agent.parser import ParsedResponse
from homeassistant.const import (
    CONF_API_KEY,
    CONF_HEADERS,
    CONF_METHOD,
    CONF_TOKEN,
    CONF_URL,
)
from homeassistant.core import HomeAssistant

from .conftest import TEST_URL


@pytest.fixture(autouse=True)
def no_retry_delay():
    """Skip the one second pause between retry attempts."""
    with patch("custom_components.http_agent.api.asyncio.sleep", AsyncMock()) as sleep:
        yield sleep


def _single_request(*side_effect):
    """Patch the single request helper with the given side effects."""
    return patch(
        "custom_components.http_agent.api._async_single_request",
        AsyncMock(side_effect=list(side_effect)),
    )


async def test_retries_until_success(hass: HomeAssistant, config_data: dict) -> None:
    """A transient failure is retried up to the configured count."""
    ok = ParsedResponse.parse('{"a": 1}', 200)
    config = {**config_data, CONF_RETRIES: 2}

    with _single_request(CannotConnect("boom"), CannotConnect("boom"), ok) as mock:
        assert await async_request(hass, config) is ok

    assert mock.call_count == 3


async def test_retries_exhausted(
    hass: HomeAssistant, config_data: dict, no_retry_delay
) -> None:
    """The last failure is raised once the attempts run out."""
    config = {**config_data, CONF_RETRIES: 1}

    with (
        _single_request(CannotConnect("a"), CannotConnect("b")) as mock,
        pytest.raises(CannotConnect),
    ):
        await async_request(hass, config)

    assert mock.call_count == 2
    assert no_retry_delay.await_count == 1


async def test_no_retries_by_default(hass: HomeAssistant, config_data: dict) -> None:
    """Without configured retries a single attempt is made."""
    with _single_request(InvalidResponse(500)) as mock, pytest.raises(InvalidResponse):
        await async_request(hass, config_data)

    assert mock.call_count == 1


async def test_auth_failures_are_not_retried(
    hass: HomeAssistant, config_data: dict
) -> None:
    """Bad credentials will not fix themselves, so do not hammer the endpoint."""
    config = {**config_data, CONF_RETRIES: 3}

    with _single_request(InvalidAuth("401")) as mock, pytest.raises(InvalidAuth):
        await async_request(hass, config)

    assert mock.call_count == 1


async def test_empty_body_is_an_error(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """An empty body is treated as a failed poll."""
    aioclient_mock.get(TEST_URL, text="   ")

    with pytest.raises(EmptyResponse):
        await async_request(hass, config_data)


async def test_head_may_return_an_empty_body(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """HEAD requests have no body by definition."""
    aioclient_mock.head(TEST_URL, text="")

    response = await async_request(hass, {**config_data, CONF_METHOD: "HEAD"})

    assert response.status == 200


async def test_error_statuses(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """4xx and 5xx map onto the right exception types."""
    aioclient_mock.get(TEST_URL, status=403)
    with pytest.raises(InvalidAuth):
        await async_request(hass, config_data)

    aioclient_mock.clear_requests()
    aioclient_mock.get(TEST_URL, status=503)
    with pytest.raises(InvalidResponse) as err:
        await async_request(hass, config_data)
    assert err.value.status == 503


async def test_templates_are_rendered(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, config_data: dict
) -> None:
    """Templates in the URL and headers are rendered on every request."""
    hass.states.async_set("input_text.city", "stockholm")
    aioclient_mock.get("http://test.local/api/stockholm", json={"ok": True})

    await async_request(
        hass,
        {
            **config_data,
            CONF_URL: "http://test.local/api/{{ states('input_text.city') }}",
            CONF_HEADERS: {"X-City": "{{ states('input_text.city') }}"},
        },
    )

    assert aioclient_mock.mock_calls[0][3]["X-City"] == "stockholm"


@pytest.mark.parametrize(
    ("config", "expected"),
    [
        ({CONF_AUTH_TYPE: AUTH_BEARER, CONF_TOKEN: "t"}, {"Authorization": "Bearer t"}),
        ({CONF_AUTH_TYPE: AUTH_API_KEY, CONF_API_KEY: "k"}, {"X-API-Key": "k"}),
        (
            {
                CONF_AUTH_TYPE: AUTH_API_KEY,
                CONF_API_KEY: "k",
                CONF_API_KEY_HEADER: "X-Token",
            },
            {"X-Token": "k"},
        ),
        ({CONF_AUTH_TYPE: "none"}, {}),
    ],
)
def test_build_request_headers(config, expected):
    assert build_request_headers(config) == expected


def test_custom_headers_override_the_preset():
    headers = build_request_headers(
        {
            CONF_AUTH_TYPE: AUTH_BEARER,
            CONF_TOKEN: "t",
            CONF_HEADERS: {"Authorization": "Custom", "Accept": "text/plain"},
        }
    )
    assert headers == {"Authorization": "Custom", "Accept": "text/plain"}


def test_redact_headers():
    redacted = redact_headers({"Authorization": "Bearer x", "Accept": "text/plain"})
    assert redacted == {"Authorization": "**REDACTED**", "Accept": "text/plain"}
