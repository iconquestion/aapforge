"""Core table validation for AAPForge-owned AA contract mappings."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

TABLE_KEYS = ("transitions", "bg_effects", "emoticons", "actions", "appears", "shapes")
TRANSITION_KEY = re.compile(r"^(None|Fade( White)?( [0-9]+)?>{0,0}|Fade( White)?( [0-9]+)? >> [0-9]+|Fade( White)? [0-9]+ >>|Fade( White)? [0-9]+ >> [0-9]+|Crossfade [0-9]+ >>|Swipe [RLDU]|Noise|Circle)$")
APPEAR_KEY = re.compile(r"^(none|al|ar|a|dl|dr|d)$")


class TableDataError(ValueError):
    pass


def load_core_tables(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_core_tables(data)
    return data


def validate_core_tables(data: dict[str, Any]) -> None:
    if data.get("schema_version") != "1.0":
        raise TableDataError("schema_version must be '1.0'")
    for key in TABLE_KEYS:
        table = data.get(key)
        if not isinstance(table, dict):
            raise TableDataError(f"{key} must be an object")
        for name, value in table.items():
            if not isinstance(name, str) or not name:
                raise TableDataError(f"{key} keys must be non-empty strings")
            if not isinstance(value, int):
                raise TableDataError(f"{key}.{name} must be an integer")
    for name in data["transitions"]:
        if not TRANSITION_KEY.match(name):
            raise TableDataError(f"bad transition key: {name}")
    for name in data["appears"]:
        if not APPEAR_KEY.match(name):
            raise TableDataError(f"bad appear key: {name}")
    if data.get("hashes") != {"background": "xxHash32:utf8:seed0"}:
        raise TableDataError("background hash contract must be xxHash32:utf8:seed0")
