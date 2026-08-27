"""Response parsing and value extraction for HTTP Agent.

A single :class:`ParsedResponse` wraps a raw HTTP response and exposes a
uniform ``extract(path)`` API regardless of whether the payload is JSON, XML,
HTML or plain text.

Path syntax per format:

* ``json`` -- dot/bracket notation, e.g. ``current.temp_c`` or ``items[0].id``.
  A leading ``$.`` is accepted so JSONPath-style paths keep working.
* ``xml``  -- ElementTree XPath, e.g. ``./current/temp_c``. Append ``/@name``
  to read an attribute instead of the element text.
* ``html`` -- CSS selector, e.g. ``#temp .value``. Append ``::attr(href)`` to
  read an attribute instead of the element text.
* ``text`` -- an optional regular expression; the first capture group (or the
  whole match) is returned. An empty path returns the whole body.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import json
import logging
import re
from typing import Any
import warnings
from xml.etree.ElementTree import Element

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning
from defusedxml.ElementTree import ParseError as DefusedParseError, fromstring

from .const import FORMAT_AUTO, FORMAT_HTML, FORMAT_JSON, FORMAT_TEXT, FORMAT_XML

_LOGGER = logging.getLogger(__name__)

_INDEX_RE = re.compile(r"\[(-?\d+)\]")
_CSS_ATTR_RE = re.compile(r"::attr\(([^)]+)\)\s*$")
_XML_ATTR_RE = re.compile(r"/?@([\w:.-]+)\s*$")


class ExtractionError(Exception):
    """Raised when a configured path cannot be resolved."""


@dataclass(slots=True)
class ParsedResponse:
    """A parsed HTTP response ready for value extraction."""

    text: str
    status: int
    headers: dict[str, str] = field(default_factory=dict)
    format: str = FORMAT_TEXT
    json_data: Any = None
    xml_data: Element | None = None
    soup: BeautifulSoup | None = None

    @classmethod
    def parse(
        cls,
        text: str,
        status: int,
        headers: dict[str, str] | None = None,
        response_format: str = FORMAT_AUTO,
    ) -> ParsedResponse:
        """Parse a raw response body into the requested (or detected) format."""
        headers = headers or {}
        content_type = headers.get("content-type", headers.get("Content-Type", ""))
        resolved = (
            _detect_format(text, content_type)
            if response_format in (FORMAT_AUTO, "", None)
            else response_format
        )

        response = cls(text=text, status=status, headers=headers, format=resolved)

        if resolved == FORMAT_JSON:
            try:
                response.json_data = json.loads(text)
            except (ValueError, TypeError):
                response.format = _detect_format(text, "")
                resolved = response.format

        if resolved == FORMAT_XML:
            try:
                response.xml_data = fromstring(text)
            except (DefusedParseError, ValueError, TypeError):
                response.format = FORMAT_HTML
                resolved = FORMAT_HTML

        if resolved == FORMAT_HTML:
            try:
                with warnings.catch_warnings():
                    # The HTML parser is a deliberate fallback for XML-ish bodies.
                    warnings.simplefilter("ignore", XMLParsedAsHTMLWarning)
                    response.soup = BeautifulSoup(text, "html.parser")
            except Exception:  # noqa: BLE001 - parser is best effort only
                response.format = FORMAT_TEXT

        return response

    def extract(self, path: str | None) -> Any:
        """Return the value at ``path``, or ``None`` when it cannot be resolved."""
        if not path:
            return None

        try:
            if self.format == FORMAT_JSON:
                return extract_json(self.json_data, path)
            if self.format == FORMAT_XML:
                return extract_xml(self.xml_data, path)
            if self.format == FORMAT_HTML:
                return extract_html(self.soup, path)
            return extract_text(self.text, path)
        except ExtractionError as err:
            _LOGGER.debug("Path '%s' could not be resolved: %s", path, err)
            return None


def _detect_format(text: str, content_type: str) -> str:
    """Guess the payload format from the content type, falling back to sniffing."""
    content_type = (content_type or "").lower()
    if "json" in content_type:
        return FORMAT_JSON
    if "html" in content_type:
        return FORMAT_HTML
    if "xml" in content_type:
        return FORMAT_XML

    stripped = text.lstrip()
    if not stripped:
        return FORMAT_TEXT
    if stripped[0] in "{[":
        try:
            json.loads(text)
        except (ValueError, TypeError):
            pass
        else:
            return FORMAT_JSON
    if stripped[:1] == "<":
        lowered = stripped[:512].lower()
        if lowered.startswith(("<!doctype html", "<html")) or "<body" in lowered:
            return FORMAT_HTML
        try:
            fromstring(text)
        except (DefusedParseError, ValueError, TypeError):
            return FORMAT_HTML
        return FORMAT_XML
    return FORMAT_TEXT


def split_json_path(path: str) -> list[str | int]:
    """Split a dot/bracket JSON path into a list of keys and indices."""
    normalised = path.strip()
    if normalised.startswith("$"):
        normalised = normalised[1:].lstrip(".")
    normalised = _INDEX_RE.sub(r".\1", normalised)

    parts: list[str | int] = []
    for raw in normalised.split("."):
        if raw == "":
            continue
        if raw.lstrip("-").isdigit():
            parts.append(int(raw))
        else:
            parts.append(raw)
    return parts


def extract_json(data: Any, path: str) -> Any:
    """Resolve a dot/bracket path inside decoded JSON data."""
    current = data
    for part in split_json_path(path):
        if isinstance(part, int):
            if not isinstance(current, (list, tuple)):
                raise ExtractionError(f"'{part}' is not a list index in '{path}'")
            try:
                current = current[part]
            except IndexError as err:
                raise ExtractionError(f"index {part} out of range in '{path}'") from err
        else:
            if not isinstance(current, dict):
                raise ExtractionError(f"'{part}' is not a mapping key in '{path}'")
            if part not in current:
                raise ExtractionError(f"key '{part}' missing in '{path}'")
            current = current[part]
    return current


def extract_xml(root: Element | None, path: str) -> Any:
    """Resolve an ElementTree XPath, optionally ending in ``/@attribute``."""
    if root is None:
        raise ExtractionError("response is not valid XML")

    attribute: str | None = None
    if match := _XML_ATTR_RE.search(path):
        attribute = match.group(1)
        path = path[: match.start()] or "."

    try:
        element = root.find(path)
    except SyntaxError as err:
        raise ExtractionError(f"invalid XPath '{path}': {err}") from err

    if element is None:
        raise ExtractionError(f"no element matched '{path}'")
    if attribute is not None:
        if attribute not in element.attrib:
            raise ExtractionError(f"attribute '{attribute}' missing on '{path}'")
        return element.attrib[attribute]
    return (element.text or "").strip()


def extract_html(soup: BeautifulSoup | None, path: str) -> Any:
    """Resolve a CSS selector, optionally ending in ``::attr(name)``."""
    if soup is None:
        raise ExtractionError("response is not valid HTML")

    attribute: str | None = None
    if match := _CSS_ATTR_RE.search(path):
        attribute = match.group(1)
        path = path[: match.start()].strip()

    try:
        element = soup.select_one(path)
    except Exception as err:
        raise ExtractionError(f"invalid CSS selector '{path}': {err}") from err

    if element is None:
        raise ExtractionError(f"no element matched '{path}'")
    if attribute is not None:
        value = element.get(attribute)
        if value is None:
            raise ExtractionError(f"attribute '{attribute}' missing on '{path}'")
        return " ".join(value) if isinstance(value, list) else value
    return element.get_text(strip=True)


def extract_text(text: str, path: str) -> Any:
    """Resolve a regular expression against a plain text body."""
    if not path or path == ".":
        return text.strip()

    try:
        pattern = re.compile(path, re.MULTILINE | re.DOTALL)
    except re.error as err:
        raise ExtractionError(f"invalid regular expression '{path}': {err}") from err

    if (match := pattern.search(text)) is None:
        raise ExtractionError(f"no match for '{path}'")
    return match.group(1) if match.groups() else match.group(0)
