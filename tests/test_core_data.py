from __future__ import annotations

import copy
from pathlib import Path

import pytest

from aapforge.data.core import CoreDataError, load_core_index, validate_core_index

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
