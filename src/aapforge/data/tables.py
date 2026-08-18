"""校验 AAPForge 自有 AA 契约映射表。"""

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
        raise TableDataError("schema_version 必须是 '1.0'")
    for key in TABLE_KEYS:
        table = data.get(key)
        if not isinstance(table, dict):
            raise TableDataError(f"{key} 必须是对象")
        for name, value in table.items():
            if not isinstance(name, str) or not name:
                raise TableDataError(f"{key} 的键必须是非空字符串")
            if not isinstance(value, int):
                raise TableDataError(f"{key}.{name} 必须是整数")
    for name in data["transitions"]:
        if not TRANSITION_KEY.match(name):
            raise TableDataError(f"过渡键不合法：{name}")
    for name in data["appears"]:
        if not APPEAR_KEY.match(name):
            raise TableDataError(f"进退场键不合法：{name}")
    if data.get("hashes") != {"background": "xxHash32:utf8:seed0"}:
        raise TableDataError("背景哈希契约必须是 xxHash32:utf8:seed0")
