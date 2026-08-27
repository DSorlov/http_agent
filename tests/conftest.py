"""Shared fixtures for the HTTP Agent tests."""

from collections.abc import Generator

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.http_agent.const import (
    AUTH_NONE,
    CONF_AUTH_TYPE,
    CONF_FOLLOW_REDIRECTS,
    CONF_RESPONSE_FORMAT,
    CONFIG_VERSION,
    DOMAIN,
    FORMAT_AUTO,
)
from homeassistant.const import (
    CONF_HEADERS,
    CONF_METHOD,
    CONF_NAME,
    CONF_SCAN_INTERVAL,
    CONF_TIMEOUT,
    CONF_URL,
    CONF_VERIFY_SSL,
)

TEST_URL = "http://test.local/api"

JSON_BODY = {
    "name": "Weather station",
    "current": {"temperature": 21.5, "humidity": 48, "is_raining": False},
    "readings": [{"value": 1}, {"value": 2}],
}

XML_BODY = """<?xml version="1.0"?>
<station id="abc">
  <current>
    <temperature unit="C">21.5</temperature>
    <humidity>48</humidity>
  </current>
  <sensor name="a">1</sensor>
  <sensor name="b">2</sensor>
</station>
"""

HTML_BODY = """<html><body>
  <div id="temp">21.5</div>
  <span class="humidity">48</span>
  <a id="link" href="/next">next</a>
</body></html>
"""


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(
    enable_custom_integrations: None,
) -> Generator[None]:
    """Enable loading of the custom integration in every test."""
    yield


@pytest.fixture
def config_data() -> dict:
    """Return a minimal version 2 config entry payload."""
    return {
        CONF_URL: TEST_URL,
        CONF_METHOD: "GET",
        CONF_AUTH_TYPE: AUTH_NONE,
        CONF_NAME: "Test endpoint",
        CONF_HEADERS: {},
        CONF_RESPONSE_FORMAT: FORMAT_AUTO,
        CONF_SCAN_INTERVAL: 60,
        CONF_TIMEOUT: 10,
        CONF_VERIFY_SSL: True,
        CONF_FOLLOW_REDIRECTS: True,
    }


@pytest.fixture
def mock_entry(config_data: dict) -> MockConfigEntry:
    """Return a config entry without any subentries."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Test endpoint",
        data=config_data,
        version=CONFIG_VERSION,
    )
