"""Core index validation for AAPForge-owned AA facts."""

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
        raise CoreDataError("schema_version must be '1.0'")
    for key in ("backgrounds", "sounds", "bgms", "characters"):
        if not isinstance(data.get(key), list):
            raise CoreDataError(f"{key} must be an array")

    _unique_named(data["backgrounds"], "backgrounds")
    _unique_named(data["sounds"], "sounds")
    _unique_field(data["bgms"], "id", "bgms")
    _unique_field(data["characters"], "id", "characters")

    for bgm in data["bgms"]:
        if not isinstance(bgm.get("id"), int):
            raise CoreDataError("bgm id must be an integer")
        if not _non_empty_string(bgm.get("name")):
            raise CoreDataError("bgm name must be a non-empty string")
        if not isinstance(bgm.get("verified"), bool):
            raise CoreDataError("bgm verified must be a boolean")

    for character in data["characters"]:
        for field in ("id", "canonical_name", "name"):
            if not _non_empty_string(character.get(field)):
                raise CoreDataError(f"character {field} must be a non-empty string")
        aliases = character.get("aliases")
        if not isinstance(aliases, list) or any(not _non_empty_string(item) for item in aliases):
            raise CoreDataError("character aliases must be non-empty strings")
        if len(set(aliases)) != len(aliases):
            raise CoreDataError("character aliases must be unique")
        if not isinstance(character.get("portrait_verified"), bool):
            raise CoreDataError("character portrait_verified must be a boolean")
        if not isinstance(character.get("spine_available"), bool):
            raise CoreDataError("character spine_available must be a boolean")
        faces = character.get("faces")
        if not isinstance(faces, list):
            raise CoreDataError("character faces must be an array")
        _unique_field(faces, "id", f"faces for {character['id']}")
        if character["portrait_verified"] and not faces:
            raise CoreDataError("portrait_verified characters must include face evidence")
        for face in faces:
            if not _non_empty_string(face.get("id")):
                raise CoreDataError("face id must be a non-empty string")
            if face.get("evidence") not in ALLOWED_FACE_EVIDENCE:
                raise CoreDataError("face evidence is not allowed")


def _unique_named(items: list[dict[str, Any]], label: str) -> None:
    for item in items:
        if not _non_empty_string(item.get("name")):
            raise CoreDataError(f"{label} name must be a non-empty string")
    _unique_field(items, "name", label)


def _unique_field(items: list[dict[str, Any]], field: str, label: str) -> None:
    values = [item.get(field) for item in items]
    if len(values) != len(set(values)):
        raise CoreDataError(f"{label} {field} values must be unique")


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
