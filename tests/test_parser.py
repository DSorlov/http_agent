"""Tests for response parsing and value extraction."""

import pytest

from custom_components.http_agent.const import (
    FORMAT_HTML,
    FORMAT_JSON,
    FORMAT_TEXT,
    FORMAT_XML,
)
from custom_components.http_agent.parser import (
    ExtractionError,
    ParsedResponse,
    extract_json,
    extract_text,
    split_json_path,
)

from .conftest import HTML_BODY, XML_BODY

XXE_BODY = """<?xml version="1.0"?>
<!DOCTYPE root [<!ENTITY xxe SYSTEM "file:///etc/passwd">]>
<root>&xxe;</root>
"""


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("a.b", ["a", "b"]),
        ("$.a.b", ["a", "b"]),
        ("items[0].id", ["items", 0, "id"]),
        ("items.0.id", ["items", 0, "id"]),
        ("", []),
    ],
)
def test_split_json_path(path, expected):
    assert split_json_path(path) == expected


def test_json_extraction():
    data = {"current": {"temp": 21.5}, "items": [{"id": "a"}, {"id": "b"}]}
    assert extract_json(data, "current.temp") == 21.5
    assert extract_json(data, "items[1].id") == "b"
    with pytest.raises(ExtractionError):
        extract_json(data, "current.missing")
    with pytest.raises(ExtractionError):
        extract_json(data, "items[9].id")


def test_json_response_detection_and_extraction():
    response = ParsedResponse.parse('{"a": {"b": 3}}', 200)
    assert response.format == FORMAT_JSON
    assert response.extract("a.b") == 3
    assert response.extract("a.missing") is None
    assert response.extract("") is None


def test_xml_response():
    response = ParsedResponse.parse(XML_BODY, 200, {"content-type": "text/xml"})
    assert response.format == FORMAT_XML
    assert response.extract("./current/temperature") == "21.5"
    assert response.extract("./current/temperature/@unit") == "C"
    assert response.extract("./sensor[2]") == "2"
    assert response.extract("./@id") == "abc"
    assert response.extract("./nope") is None


def test_xml_external_entities_are_rejected():
    """Defused XML must refuse the payload rather than reading local files."""
    response = ParsedResponse.parse(XXE_BODY, 200, {"content-type": "text/xml"})
    assert response.format != FORMAT_XML
    assert "root" not in (response.extract("./root") or "")


def test_html_response():
    response = ParsedResponse.parse(HTML_BODY, 200, {"content-type": "text/html"})
    assert response.format == FORMAT_HTML
    assert response.extract("#temp") == "21.5"
    assert response.extract(".humidity") == "48"
    assert response.extract("#link::attr(href)") == "/next"
    assert response.extract("#missing") is None


def test_text_response():
    response = ParsedResponse.parse("temperature=21.5 C", 200)
    assert response.format == FORMAT_TEXT
    assert response.extract(".") == "temperature=21.5 C"
    assert response.extract(r"temperature=([\d.]+)") == "21.5"
    assert response.extract("nomatch") is None


def test_text_extraction_rejects_invalid_regex():
    with pytest.raises(ExtractionError):
        extract_text("body", "[unclosed")


def test_forced_format_falls_back_when_body_does_not_match():
    response = ParsedResponse.parse("not json at all", 200, response_format=FORMAT_JSON)
    assert response.format == FORMAT_TEXT
