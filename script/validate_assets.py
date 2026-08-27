#!/usr/bin/env python3
"""Validate that translations and brand assets stay in sync with the source.

Run locally with ``python script/validate_assets.py``; the CI workflow runs the
same checks on every pull request.
"""

from __future__ import annotations

import json
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parent.parent
COMPONENT = ROOT / "custom_components" / "http_agent"
TRANSLATIONS = COMPONENT / "translations"
BRANDS = ROOT / "brands" / "custom_integrations" / "http_agent"

EXPECTED_ICON_SIZES = {"icon.png": (256, 256), "icon@2x.png": (512, 512)}
MAX_LOGO_SIZES = {"logo.png": (512, 256), "logo@2x.png": (1024, 512)}


def key_paths(node: object, prefix: str = "") -> set[str]:
    """Return every leaf path in a nested JSON structure."""
    if not isinstance(node, dict):
        return {prefix}
    paths: set[str] = set()
    for key, value in node.items():
        paths |= key_paths(value, f"{prefix}.{key}" if prefix else key)
    return paths


def png_size(path: Path) -> tuple[int, int]:
    """Return the pixel dimensions of a PNG file."""
    header = path.read_bytes()[:24]
    if header[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"{path} is not a PNG file")
    width, height = struct.unpack(">II", header[16:24])
    return width, height


def check_translations() -> list[str]:
    """Every translation file must have exactly the keys of strings.json."""
    errors: list[str] = []
    reference = json.loads((COMPONENT / "strings.json").read_text(encoding="utf-8"))
    expected = key_paths(reference)

    files = sorted(TRANSLATIONS.glob("*.json"))
    if not files:
        return ["no translation files found"]

    for file in files:
        actual = key_paths(json.loads(file.read_text(encoding="utf-8")))
        for path in sorted(expected - actual):
            errors.append(f"{file.name}: missing key '{path}'")
        for path in sorted(actual - expected):
            errors.append(f"{file.name}: unknown key '{path}'")
    return errors


def check_brands() -> list[str]:
    """Brand assets must match the home-assistant/brands requirements."""
    errors: list[str] = []

    for name, expected in EXPECTED_ICON_SIZES.items():
        path = BRANDS / name
        if not path.is_file():
            errors.append(f"brands: {name} is missing")
            continue
        if (actual := png_size(path)) != expected:
            errors.append(f"brands: {name} is {actual}, expected {expected}")

    for name, (max_width, max_height) in MAX_LOGO_SIZES.items():
        path = BRANDS / name
        if not path.is_file():
            continue
        width, height = png_size(path)
        if width > max_width or height > max_height:
            errors.append(
                f"brands: {name} is {width}x{height}, "
                f"maximum is {max_width}x{max_height}"
            )
    return errors


def main() -> int:
    """Run all checks and report the result."""
    errors = check_translations() + check_brands()
    for error in errors:
        print(f"error: {error}", file=sys.stderr)  # noqa: T201
    if errors:
        return 1
    print("translations and brand assets are valid")  # noqa: T201
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
