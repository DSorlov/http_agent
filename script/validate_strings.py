#!/usr/bin/env python3
"""Validate strings.json and the translations against the hassfest rules.

This mirrors ``script/hassfest/translations.py`` from Home Assistant core so the
same problems are caught locally, without needing a core checkout.
"""

from __future__ import annotations

import json
from pathlib import Path
import re
import string
import sys
from typing import Any

import voluptuous as vol

import homeassistant.helpers.config_validation as cv

COMPONENT = Path(__file__).resolve().parent.parent / "custom_components" / "http_agent"

RE_COMBINED_REFERENCE = re.compile(r"(.+\[%)|(%\].+)")
RE_PLACEHOLDER_IN_SINGLE_QUOTES = re.compile(r"'{\w+}'")
RE_URL = re.compile(
    r"(((ftp|ftps|scp|http|https|mqtt|mqtts|socket|socks5):\/\/|www\.)"
    r"[a-z0-9]+([\-\.]{1}[a-z0-9]+)*\.[a-z]{2,5}(:[0-9]{1,5})?(\/.*)?)",
    re.IGNORECASE,
)


def value(raw: Any) -> str:
    """Validate a single translated string."""
    text = cv.string_with_no_html(raw)
    if RE_PLACEHOLDER_IN_SINGLE_QUOTES.search(text):
        raise vol.Invalid("placeholders must not be wrapped in single quotes")
    for _, field, _, _ in string.Formatter().parse(text):
        if field and not field.isidentifier():
            raise vol.Invalid(f"invalid placeholder {field!r}")
    if RE_COMBINED_REFERENCE.search(text):
        raise vol.Invalid("the string must not contain combined translations")
    if text != text.strip():
        raise vol.Invalid("the string must not have leading or trailing spaces")
    if RE_URL.search(text):
        raise vol.Invalid("the string must not contain URLs")
    return text


def data_entry_schema(*, subentry: bool = False) -> vol.All:
    """Build the schema for a config, options or subentry flow."""
    schema: dict[Any, Any] = {
        vol.Optional("flow_title"): value,
        vol.Required("step"): {
            str: {
                vol.Optional("title"): value,
                vol.Optional("description"): value,
                vol.Optional("data"): {str: value},
                vol.Optional("data_description"): {str: value},
                vol.Optional("menu_options"): {str: value},
                vol.Optional("submit"): value,
                vol.Optional("sections"): {
                    str: {
                        vol.Optional("data"): {str: value},
                        vol.Optional("data_description"): {str: value},
                        vol.Optional("description"): value,
                        vol.Optional("name"): value,
                    }
                },
            }
        },
        vol.Optional("error"): {str: value},
        vol.Optional("abort"): {str: value},
        vol.Optional("progress"): {str: value},
        vol.Optional("create_entry"): {str: value},
    }
    if subentry:
        schema[vol.Required("entry_type")] = value
        schema[vol.Required("initiate_flow")] = {
            vol.Required("user"): value,
            str: value,
        }

    def descriptions_match_data(flow: dict[str, Any]) -> dict[str, Any]:
        """Every data_description key must have a matching data key."""
        for step_id, step in flow["step"].items():
            for key in step.get("data_description", {}):
                if key not in step.get("data", {}):
                    raise vol.Invalid(f"{step_id}: '{key}' is not in data")
            for section_id, section in step.get("sections", {}).items():
                for key in section.get("data_description", {}):
                    if key not in section.get("data", {}):
                        raise vol.Invalid(
                            f"{step_id}.{section_id}: '{key}' is not in data"
                        )
        return flow

    return vol.All(vol.Schema(schema), descriptions_match_data)


SCHEMA = vol.Schema(
    {
        vol.Optional("title"): value,
        vol.Optional("config"): data_entry_schema(),
        vol.Optional("config_subentries"): cv.schema_with_slug_keys(
            data_entry_schema(subentry=True), slug_validator=cv.slug
        ),
        vol.Optional("options"): data_entry_schema(),
        vol.Optional("exceptions"): cv.schema_with_slug_keys(
            {vol.Optional("message"): value}, slug_validator=cv.slug
        ),
    }
)


def main() -> int:
    """Validate every translation file."""
    files = [COMPONENT / "strings.json"]
    files += sorted((COMPONENT / "translations").glob("*.json"))

    failed = False
    for path in files:
        try:
            SCHEMA(json.loads(path.read_text(encoding="utf-8")))
        except vol.Invalid as err:
            failed = True
            print(f"error: {path.name}: {err}", file=sys.stderr)  # noqa: T201

    if failed:
        return 1
    print(f"{len(files)} translation files are valid")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
