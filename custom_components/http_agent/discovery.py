"""Discover selectable values in an HTTP response.

The config flow performs a live test request and then uses this module to turn
the response into a flat, human readable list of candidate values. The user
picks the ones that should become entities instead of hand-writing paths.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import re
from typing import Any
from xml.etree.ElementTree import Element

from bs4 import BeautifulSoup, Tag

from homeassistant.components.binary_sensor import BinarySensorDeviceClass
from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass

from .const import (
    FALSY_VALUES,
    FORMAT_HTML,
    FORMAT_JSON,
    FORMAT_XML,
    MAX_DISCOVERED_VALUES,
    MAX_DISCOVERY_DEPTH,
    SUBENTRY_TYPE_BINARY_SENSOR,
    SUBENTRY_TYPE_SENSOR,
    TRUTHY_VALUES,
)
from .parser import ParsedResponse

# Maximum number of list items expanded per array, to keep large collections sane.
_MAX_LIST_ITEMS = 20
# Text longer than this is unlikely to be a useful entity state.
_MAX_TEXT_LENGTH = 120
# Value previews shown in the picker are truncated to this many characters.
_MAX_PREVIEW_LENGTH = 60

_SPLIT_RE = re.compile(r"[^0-9A-Za-z]+")

# Key fragment -> (device class, unit, state class). Ordered: first match wins.
_DEVICE_CLASS_HINTS: tuple[tuple[str, SensorDeviceClass, str | None], ...] = (
    ("temperature", SensorDeviceClass.TEMPERATURE, "°C"),
    ("temp", SensorDeviceClass.TEMPERATURE, "°C"),
    ("humidity", SensorDeviceClass.HUMIDITY, "%"),
    ("battery", SensorDeviceClass.BATTERY, "%"),
    ("pressure", SensorDeviceClass.PRESSURE, "hPa"),
    ("illuminance", SensorDeviceClass.ILLUMINANCE, "lx"),
    ("lux", SensorDeviceClass.ILLUMINANCE, "lx"),
    ("co2", SensorDeviceClass.CO2, "ppm"),
    ("carbon_dioxide", SensorDeviceClass.CO2, "ppm"),
    ("pm25", SensorDeviceClass.PM25, "µg/m³"),
    ("pm10", SensorDeviceClass.PM10, "µg/m³"),
    ("energy", SensorDeviceClass.ENERGY, "kWh"),
    ("power", SensorDeviceClass.POWER, "W"),
    ("voltage", SensorDeviceClass.VOLTAGE, "V"),
    ("current", SensorDeviceClass.CURRENT, "A"),
    ("frequency", SensorDeviceClass.FREQUENCY, "Hz"),
    ("rssi", SensorDeviceClass.SIGNAL_STRENGTH, "dBm"),
    ("signal", SensorDeviceClass.SIGNAL_STRENGTH, "dBm"),
    ("wind_speed", SensorDeviceClass.WIND_SPEED, "km/h"),
    ("speed", SensorDeviceClass.SPEED, "km/h"),
    ("distance", SensorDeviceClass.DISTANCE, "km"),
    ("price", SensorDeviceClass.MONETARY, None),
    ("cost", SensorDeviceClass.MONETARY, None),
    ("timestamp", SensorDeviceClass.TIMESTAMP, None),
)

_BINARY_DEVICE_CLASS_HINTS: tuple[tuple[str, BinarySensorDeviceClass], ...] = (
    ("motion", BinarySensorDeviceClass.MOTION),
    ("door", BinarySensorDeviceClass.DOOR),
    ("window", BinarySensorDeviceClass.WINDOW),
    ("moisture", BinarySensorDeviceClass.MOISTURE),
    ("leak", BinarySensorDeviceClass.MOISTURE),
    ("smoke", BinarySensorDeviceClass.SMOKE),
    ("online", BinarySensorDeviceClass.CONNECTIVITY),
    ("connected", BinarySensorDeviceClass.CONNECTIVITY),
    ("charging", BinarySensorDeviceClass.BATTERY_CHARGING),
    ("occupancy", BinarySensorDeviceClass.OCCUPANCY),
    ("presence", BinarySensorDeviceClass.PRESENCE),
    ("problem", BinarySensorDeviceClass.PROBLEM),
    ("error", BinarySensorDeviceClass.PROBLEM),
    ("lock", BinarySensorDeviceClass.LOCK),
    ("running", BinarySensorDeviceClass.RUNNING),
)

_TOTAL_INCREASING = {
    SensorDeviceClass.ENERGY,
    SensorDeviceClass.GAS,
    SensorDeviceClass.WATER,
}

_BOOLEAN_PREFIXES = ("is_", "has_", "can_", "should_", "enable", "allow")


@dataclass(slots=True)
class DiscoveredValue:
    """A single addressable value found in a response."""

    path: str
    value: Any

    @property
    def key(self) -> str:
        """Return the trailing path segment, without indices or attribute markers."""
        segment = re.split(r"[./]", self.path.rstrip("/"))[-1]
        segment = re.sub(r"\[\d+\]$", "", segment)
        return segment.lstrip("@").strip() or self.path

    @property
    def name(self) -> str:
        """Return a human friendly entity name derived from the path."""
        words = [word for word in _SPLIT_RE.split(self.key) if word]
        if not words:
            return self.path
        return " ".join(words).strip().capitalize()

    @property
    def preview(self) -> str:
        """Return a short, single line rendering of the value."""
        text = "null" if self.value is None else str(self.value)
        text = " ".join(text.split())
        if len(text) <= _MAX_PREVIEW_LENGTH:
            return text
        return f"{text[: _MAX_PREVIEW_LENGTH - 1]}…"

    @property
    def label(self) -> str:
        """Return the label shown in the value picker."""
        return f"{self.path} = {self.preview}"

    @property
    def is_boolean(self) -> bool:
        """Return True when the value looks like an on/off state."""
        if isinstance(self.value, bool):
            return True
        if isinstance(self.value, str):
            lowered = self.value.strip().lower()
            if lowered in TRUTHY_VALUES or lowered in FALSY_VALUES:
                return True
        return self.key.lower().startswith(_BOOLEAN_PREFIXES)

    @property
    def is_numeric(self) -> bool:
        """Return True when the value can be represented as a number."""
        if isinstance(self.value, bool):
            return False
        if isinstance(self.value, (int, float)):
            return True
        if isinstance(self.value, str):
            try:
                float(self.value.strip().replace(",", "."))
            except ValueError:
                return False
            return True
        return False

    @property
    def suggested_platform(self) -> str:
        """Return the subentry type that fits this value best."""
        if self.is_boolean:
            return SUBENTRY_TYPE_BINARY_SENSOR
        return SUBENTRY_TYPE_SENSOR

    @property
    def suggested_device_class(self) -> str | None:
        """Return a device class guessed from the key name."""
        key = self.key.lower()
        if self.suggested_platform == SUBENTRY_TYPE_BINARY_SENSOR:
            for fragment, device_class in _BINARY_DEVICE_CLASS_HINTS:
                if fragment in key:
                    return device_class.value
            return None
        if not self.is_numeric and not _looks_like_timestamp(self.value):
            return None
        for fragment, device_class, _unit in _DEVICE_CLASS_HINTS:
            if fragment in key:
                return device_class.value
        return None

    @property
    def suggested_unit(self) -> str | None:
        """Return a unit of measurement guessed from the key name."""
        if self.suggested_platform != SUBENTRY_TYPE_SENSOR or not self.is_numeric:
            return None
        key = self.key.lower()
        for fragment, _device_class, unit in _DEVICE_CLASS_HINTS:
            if fragment in key:
                return unit
        return None

    @property
    def suggested_state_class(self) -> str | None:
        """Return a state class guessed from the value and device class."""
        if self.suggested_platform != SUBENTRY_TYPE_SENSOR or not self.is_numeric:
            return None
        device_class = self.suggested_device_class
        if device_class in _TOTAL_INCREASING:
            return SensorStateClass.TOTAL_INCREASING.value
        if device_class == SensorDeviceClass.TIMESTAMP.value:
            return None
        return SensorStateClass.MEASUREMENT.value


def discover_values(response: ParsedResponse) -> list[DiscoveredValue]:
    """Return every addressable value in ``response``, capped for UI sanity."""
    found: list[DiscoveredValue] = []

    if response.format == FORMAT_JSON:
        _walk_json(response.json_data, "", found, 0)
    elif response.format == FORMAT_XML:
        if response.xml_data is not None:
            _walk_xml(response.xml_data, ".", found, 0)
    elif response.format == FORMAT_HTML:
        if response.soup is not None:
            _walk_html(response.soup, found)
    elif response.text.strip():
        found.append(DiscoveredValue(path=".", value=response.text.strip()))

    return found[:MAX_DISCOVERED_VALUES]


def _walk_json(
    data: Any, prefix: str, found: list[DiscoveredValue], depth: int
) -> None:
    """Recursively flatten JSON data into dot/bracket paths."""
    if depth > MAX_DISCOVERY_DEPTH or len(found) >= MAX_DISCOVERED_VALUES:
        return

    if isinstance(data, dict):
        for key, value in data.items():
            child = f"{prefix}.{key}" if prefix else str(key)
            _walk_json(value, child, found, depth + 1)
    elif isinstance(data, list):
        for index, value in enumerate(data[:_MAX_LIST_ITEMS]):
            _walk_json(value, f"{prefix}[{index}]", found, depth + 1)
    elif prefix:
        found.append(DiscoveredValue(path=prefix, value=data))


def _walk_xml(
    element: Element, prefix: str, found: list[DiscoveredValue], depth: int
) -> None:
    """Recursively flatten an XML tree into ElementTree XPath expressions."""
    if depth > MAX_DISCOVERY_DEPTH or len(found) >= MAX_DISCOVERED_VALUES:
        return

    for name, value in element.attrib.items():
        found.append(DiscoveredValue(path=f"{prefix}/@{name}", value=value))

    children = list(element)
    text = (element.text or "").strip()
    if text and not children:
        found.append(DiscoveredValue(path=prefix, value=text))

    totals = Counter(child.tag for child in children)
    seen: Counter[str] = Counter()
    for child in children:
        seen[child.tag] += 1
        suffix = f"[{seen[child.tag]}]" if totals[child.tag] > 1 else ""
        _walk_xml(child, f"{prefix}/{child.tag}{suffix}", found, depth + 1)


def _walk_html(soup: BeautifulSoup, found: list[DiscoveredValue]) -> None:
    """Collect leaf elements that carry short text, addressed by CSS selector."""
    for element in soup.find_all(True):
        if len(found) >= MAX_DISCOVERED_VALUES:
            return
        if element.name in ("script", "style", "head", "meta", "link", "title"):
            continue
        if any(isinstance(child, Tag) for child in element.children):
            continue
        text = element.get_text(strip=True)
        if not text or len(text) > _MAX_TEXT_LENGTH:
            continue
        if (selector := _css_selector(soup, element)) is not None:
            found.append(DiscoveredValue(path=selector, value=text))


def _css_selector(soup: BeautifulSoup, element: Tag) -> str | None:
    """Build the shortest CSS selector that uniquely matches ``element``."""
    if element_id := element.get("id"):
        candidate = f"#{element_id}"
        if _matches_only(soup, candidate, element):
            return candidate

    classes = [cls for cls in element.get("class", []) if cls]
    if classes:
        candidate = f"{element.name}." + ".".join(classes)
        if _matches_only(soup, candidate, element):
            return candidate

    parts: list[str] = []
    current: Tag | None = element
    while isinstance(current, Tag) and current.name != "[document]":
        parent = current.parent
        if not isinstance(parent, Tag):
            break
        index = 1 + sum(
            1
            for sibling in current.previous_siblings
            if isinstance(sibling, Tag) and sibling.name == current.name
        )
        parts.append(f"{current.name}:nth-of-type({index})")
        candidate = " > ".join(reversed(parts))
        if _matches_only(soup, candidate, element):
            return candidate
        current = parent
    return None


def _matches_only(soup: BeautifulSoup, selector: str, element: Tag) -> bool:
    """Return True when ``selector`` resolves to exactly ``element``."""
    try:
        matches = soup.select(selector, limit=2)
    except Exception:  # noqa: BLE001 - soupsieve raises many types
        return False
    return len(matches) == 1 and matches[0] is element


def _looks_like_timestamp(value: Any) -> bool:
    """Return True for ISO-8601-ish strings."""
    return isinstance(value, str) and bool(
        re.match(r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}", value.strip())
    )
