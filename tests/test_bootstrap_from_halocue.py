from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from aapforge.data.bootstrap import BootstrapError, build_core_candidate
from aapforge.data.core import load_core_index, validate_core_index

ROOT = Path(__file__).resolve().parents[1]
HALOCUE_FIXTURE = ROOT / "tests/fixtures/halocue/minimal_aa_resources.json"
CORE_FIXTURE = ROOT / "tests/fixtures/core/minimal_real_core.json"
ALLOWLIST = ROOT / "tools/bootstrap_allowlist.json"
TABLES = ROOT / "resources/core/tables.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _candidate(source: dict | None = None, allowlist: dict | None = None) -> dict:
    return build_core_candidate(
        source or _load(HALOCUE_FIXTURE),
        allowlist or _load(ALLOWLIST),
        tables_path=str(TABLES),
    )


def test_minimal_halocue_fixture_builds_expected_candidate():
    candidate = _candidate()
    assert candidate == _load(CORE_FIXTURE)
    validate_core_index(candidate)


def test_candidate_does_not_leak_halocue_source_path():
    source = _load(HALOCUE_FIXTURE)
    source["_source"] = "D:/private/AA"
    payload = json.dumps(_candidate(source), ensure_ascii=False, sort_keys=True)
    assert "D:/private/AA" not in payload
    assert "fixture-aa-data-root" not in payload


def test_custom_override_character_is_rejected():
    source = _load(HALOCUE_FIXTURE)
    source["characters"][0]["source"] = "custom_override"
    with pytest.raises(BootstrapError) as error:
        _candidate(source)
    assert error.value.code == "E_BOOTSTRAP_UNOFFICIAL_CHARACTER"


def test_ambiguous_character_name_is_rejected():
    source = _load(HALOCUE_FIXTURE)
    duplicate = copy.deepcopy(source["characters"][0])
    duplicate["identifier"] = "MomoiAlt"
    source["characters"].append(duplicate)
    with pytest.raises(BootstrapError) as error:
        _candidate(source)
    assert error.value.code == "E_BOOTSTRAP_AMBIGUOUS_CHARACTER"


def test_background_hash_conflict_is_rejected():
    source = _load(HALOCUE_FIXTURE)
    source["bg"]["BG_Black"] = 1
    with pytest.raises(BootstrapError) as error:
        _candidate(source)
    assert error.value.code == "E_BOOTSTRAP_BACKGROUND_HASH_CONFLICT"


def test_halo_bg_conflict_is_rejected():
    source = _load(HALOCUE_FIXTURE)
    source["bg_conflict"] = ["BG_Black"]
    with pytest.raises(BootstrapError) as error:
        _candidate(source)
    assert error.value.code == "E_BOOTSTRAP_BG_CONFLICT"


def test_candidate_only_face_is_rejected():
    source = _load(HALOCUE_FIXTURE)
    source["face_capabilities"]["Momoi"][0]["faces"].append(
        {
            "id": "04",
            "raw": "04",
            "label": "embarrassed",
            "cn": "",
            "sources": ["atlas_candidate"],
            "observed_count": 0,
            "verified": False,
        }
    )
    allowlist = _load(ALLOWLIST)
    allowlist["faces"]["桃井"] = ["04"]
    with pytest.raises(BootstrapError) as error:
        _candidate(source, allowlist)
    assert error.value.code == "E_BOOTSTRAP_FACE_NOT_OBSERVED"


def test_character_without_face_variants_still_builds_identity():
    source = _load(HALOCUE_FIXTURE)
    source["face_capabilities"]["Momoi"] = []
    candidate = _candidate(source)
    character = candidate["characters"][0]
    assert character["id"] == "Momoi"
    assert "outfit_key" not in character
    assert "variant" not in character


def test_character_with_single_variant_still_builds_identity():
    candidate = _candidate()
    character = candidate["characters"][0]
    assert character["id"] == "Momoi"
    assert "outfit_key" not in character
    assert "spine" not in character


def test_character_with_multiple_variants_still_builds_identity_without_guessing():
    source = _load(HALOCUE_FIXTURE)
    variant = copy.deepcopy(source["face_capabilities"]["Momoi"][0])
    variant["outfit_key"] = "Momoi_Alt"
    source["face_capabilities"]["Momoi"].append(variant)
    allowlist = _load(ALLOWLIST)
    allowlist["faces"]["桃井"] = []
    candidate = _candidate(source, allowlist)
    character = candidate["characters"][0]
    assert character["id"] == "Momoi"
    assert character["faces"] == []
    assert character["portrait_verified"] is False
    assert "outfit_key" not in character
    assert "spine" not in character


def test_multiple_variants_reject_requested_face_without_unique_variant():
    source = _load(HALOCUE_FIXTURE)
    variant = copy.deepcopy(source["face_capabilities"]["Momoi"][0])
    variant["outfit_key"] = "Momoi_Alt"
    source["face_capabilities"]["Momoi"].append(variant)
    allowlist = _load(ALLOWLIST)
    allowlist["faces"]["桃井"] = ["03"]
    with pytest.raises(BootstrapError) as error:
        _candidate(source, allowlist)
    assert error.value.code == "E_BOOTSTRAP_AMBIGUOUS_FACE_VARIANT"


def test_single_variant_still_promotes_requested_observed_face():
    candidate = _candidate()
    character = candidate["characters"][0]
    assert [face["id"] for face in character["faces"]] == ["00", "03"]
    assert character["portrait_verified"] is True


def test_spine_available_uses_actual_spine_field():
    with_spine = _candidate()
    assert with_spine["characters"][0]["spine_available"] is True

    source = _load(HALOCUE_FIXTURE)
    source["characters"][0]["spine"] = ""
    without_spine = _candidate(source)
    assert without_spine["characters"][0]["spine_available"] is False


def test_empty_faces_mean_unverified_not_absent():
    source = _load(HALOCUE_FIXTURE)
    source["faces_used"]["Momoi"] = []
    allowlist = _load(ALLOWLIST)
    allowlist["faces"]["桃井"] = []
    candidate = _candidate(source, allowlist)
    character = candidate["characters"][0]
    assert character["faces"] == []
    assert character["portrait_verified"] is False
    assert character["spine_available"] is True


def test_missing_observed_face_is_rejected():
    allowlist = _load(ALLOWLIST)
    allowlist["faces"]["桃井"] = ["05"]
    with pytest.raises(BootstrapError) as error:
        _candidate(allowlist=allowlist)
    assert error.value.code == "E_BOOTSTRAP_ALLOWLIST_MISSING_FACE"


def test_enum_conflict_is_rejected():
    source = _load(HALOCUE_FIXTURE)
    source["enums"]["action"]["6"]["verb"] = "wrong"
    with pytest.raises(BootstrapError) as error:
        _candidate(source)
    assert error.value.code == "E_BOOTSTRAP_ENUM_CONFLICT"


def test_verify_core_data_accepts_candidate_path_fixture():
    loaded = load_core_index(CORE_FIXTURE)
    assert loaded["characters"][0]["id"] == "Momoi"
