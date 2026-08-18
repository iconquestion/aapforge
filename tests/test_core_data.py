from __future__ import annotations

import copy
from pathlib import Path

import pytest

from aapforge.data.core import (
    CharacterNameAmbiguousError,
    CharacterNameNotFoundError,
    CoreDataError,
    load_core_index,
    resolve_character_by_name,
    validate_core_index,
)

ROOT = Path(__file__).resolve().parents[1]


def test_valid_core_index_passes():
    load_core_index(ROOT / "resources/core/index.json")


def test_duplicate_character_fails():
    data = load_core_index(ROOT / "resources/core/index.json")
    character = {
        "id": "alice",
        "canonical_name": "Alice",
        "name": "Alice",
        "aliases": [],
        "portrait_verified": True,
        "spine_available": True,
        "faces": [{"id": "00", "evidence": "observed"}],
    }
    data["characters"] = [character, copy.deepcopy(character)]
    with pytest.raises(CoreDataError):
        validate_core_index(data)


def test_duplicate_face_fails():
    data = load_core_index(ROOT / "resources/core/index.json")
    data["characters"] = [
        {
            "id": "alice",
            "canonical_name": "Alice",
            "name": "Alice",
            "aliases": [],
            "portrait_verified": True,
            "spine_available": True,
            "faces": [
                {"id": "00", "evidence": "observed"},
                {"id": "00", "evidence": "observed"},
            ],
        }
    ]
    with pytest.raises(CoreDataError):
        validate_core_index(data)


def test_invalid_evidence_fails():
    data = load_core_index(ROOT / "resources/core/index.json")
    data["characters"] = [
        {
            "id": "alice",
            "canonical_name": "Alice",
            "name": "Alice",
            "aliases": [],
            "portrait_verified": True,
            "spine_available": True,
            "faces": [{"id": "00", "evidence": "guessed"}],
        }
    ]
    with pytest.raises(CoreDataError):
        validate_core_index(data)


def test_duplicate_bgm_id_fails():
    data = load_core_index(ROOT / "resources/core/index.json")
    data["bgms"] = [
        {"id": 123, "name": "A", "verified": True},
        {"id": 123, "name": "B", "verified": True},
    ]
    with pytest.raises(CoreDataError):
        validate_core_index(data)


def test_resolve_unique_character_name_passes():
    data = load_core_index(ROOT / "resources/core/index.json")
    data["characters"] = [
        _character("alice", "Alice", aliases=["Alicia"]),
        _character("bob", "Bob"),
    ]
    assert resolve_character_by_name(data, "Alice")["id"] == "alice"
    assert resolve_character_by_name(data, "Alicia")["id"] == "alice"


def test_resolve_missing_character_name_fails():
    data = load_core_index(ROOT / "resources/core/index.json")
    data["characters"] = [_character("alice", "Alice")]
    with pytest.raises(CharacterNameNotFoundError):
        resolve_character_by_name(data, "Carol")


def test_resolve_ambiguous_character_name_fails():
    data = load_core_index(ROOT / "resources/core/index.json")
    data["characters"] = [
        _character("alice-main", "Alice"),
        _character("alice-alt", "Alice"),
    ]
    with pytest.raises(CharacterNameAmbiguousError):
        resolve_character_by_name(data, "Alice")


def test_resolve_alias_conflict_fails():
    data = load_core_index(ROOT / "resources/core/index.json")
    data["characters"] = [
        _character("alice", "Alice", aliases=["Shared"]),
        _character("bob", "Bob", aliases=["Shared"]),
    ]
    with pytest.raises(CharacterNameAmbiguousError):
        resolve_character_by_name(data, "Shared")


def _character(identifier: str, name: str, *, aliases: list[str] | None = None) -> dict:
    return {
        "id": identifier,
        "canonical_name": name,
        "name": name,
        "aliases": aliases or [],
        "portrait_verified": False,
        "spine_available": False,
        "faces": [],
    }
