"""校验 AAPForge 自有 AA 事实核心索引。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ALLOWED_FACE_EVIDENCE = {"observed", "halocue"}


class CoreDataError(ValueError):
    pass


def load_core_index(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    validate_core_index(data)
    return data


def validate_core_index(data: dict[str, Any]) -> None:
    if data.get("schema_version") != "1.0":
        raise CoreDataError("schema_version 必须是 '1.0'")
    for key in ("backgrounds", "sounds", "bgms", "characters"):
        if not isinstance(data.get(key), list):
            raise CoreDataError(f"{key} 必须是数组")

    _unique_named(data["backgrounds"], "backgrounds")
    _unique_named(data["sounds"], "sounds")
    _unique_field(data["bgms"], "id", "bgms")
    _unique_field(data["characters"], "id", "characters")

    for bgm in data["bgms"]:
        if not isinstance(bgm.get("id"), int):
            raise CoreDataError("bgm id 必须是整数")
        if not _non_empty_string(bgm.get("name")):
            raise CoreDataError("bgm name 必须是非空字符串")
        if not isinstance(bgm.get("verified"), bool):
            raise CoreDataError("背景音乐 verified 字段必须是布尔值")

    for character in data["characters"]:
        for field in ("id", "canonical_name", "name"):
            if not _non_empty_string(character.get(field)):
                raise CoreDataError(f"character {field} 必须是非空字符串")
        aliases = character.get("aliases")
        if not isinstance(aliases, list) or any(not _non_empty_string(item) for item in aliases):
            raise CoreDataError("character aliases 必须是非空字符串")
        if len(set(aliases)) != len(aliases):
            raise CoreDataError("character aliases 必须唯一")
        if not isinstance(character.get("portrait_verified"), bool):
            raise CoreDataError("角色 portrait_verified 字段必须是布尔值")
        if not isinstance(character.get("spine_available"), bool):
            raise CoreDataError("character spine_available 必须是布尔值")
        faces = character.get("faces")
        if not isinstance(faces, list):
            raise CoreDataError("character faces 必须是数组")
        _unique_field(faces, "id", f"faces for {character['id']}")
        if character["portrait_verified"] and not faces:
            raise CoreDataError("portrait_verified 为 true 的角色必须包含表情编号证据")
        for face in faces:
            if not _non_empty_string(face.get("id")):
                raise CoreDataError("face id 必须是非空字符串")
            if face.get("evidence") not in ALLOWED_FACE_EVIDENCE:
                raise CoreDataError("face evidence 不在允许集合内")


def _unique_named(items: list[dict[str, Any]], label: str) -> None:
    for item in items:
        if not _non_empty_string(item.get("name")):
            raise CoreDataError(f"{label} name 必须是非空字符串")
    _unique_field(items, "name", label)


def _unique_field(items: list[dict[str, Any]], field: str, label: str) -> None:
    values = [item.get(field) for item in items]
    if len(values) != len(set(values)):
        raise CoreDataError(f"{label} {field} 的值必须唯一")


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
