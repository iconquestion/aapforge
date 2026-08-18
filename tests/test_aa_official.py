from __future__ import annotations

import base64
import copy
import json
import struct

import pytest

from aapforge.data.aa_official import (
    AaOfficialDataError,
    build_official_character_data,
    normalize_character_rows,
)
from tools.extract_aa_official import (
    CharacterBundleAmbiguousError,
    CharacterBundleNotFoundError,
    discover_cache_candidates,
    locate_character_bundle,
    resolve_character_bundle_for_cli,
    resolve_character_bundle_from_discovered_caches,
)


def test_single_character_record_normalizes_to_character_fact():
    characters = normalize_character_rows(
        [
            _row(
                identifier="hoshino",
                name="星野",
                native_key=123,
                shape=3,
                spine="UIs/CharacterSpine_hoshino",
                avatar="UIs/NPC_Portrait_hoshino",
            )
        ]
    )
    assert characters == [
        {
            "id": "hoshino",
            "canonical_name": "星野",
            "name": "星野",
            "aliases": [],
            "spine_available": True,
            "portrait_verified": False,
            "faces": [],
            "records": [
                {
                    "native_key": 123,
                    "shape": 3,
                    "club": "GameDev",
                    "spine": "UIs/CharacterSpine_hoshino",
                    "avatar": "UIs/NPC_Portrait_hoshino",
                }
            ],
            "evidence": [{"kind": "official", "source": "aa:ScenarioCharacterNameExcel"}],
        }
    ]


def test_all_records_without_spine_make_spine_unavailable():
    characters = normalize_character_rows([_row(spine="", avatar="UIs/NPC_Portrait_Null")])
    assert characters[0]["spine_available"] is False


def test_duplicate_identifier_preserves_complete_records():
    characters = normalize_character_rows(
        [
            _row(native_key=2, shape=4, spine="Spine_B", avatar="Avatar_B"),
            _row(native_key=1, shape=3, spine="Spine_A", avatar="Avatar_A"),
        ]
    )
    assert len(characters) == 1
    assert characters[0]["records"] == [
        {"native_key": 1, "shape": 3, "club": "GameDev", "spine": "Spine_A", "avatar": "Avatar_A"},
        {"native_key": 2, "shape": 4, "club": "GameDev", "spine": "Spine_B", "avatar": "Avatar_B"},
    ]
    assert "variant_native_keys" not in characters[0]


def test_duplicate_identifier_preserves_record_level_club():
    characters = normalize_character_rows(
        [
            _row(native_key=2, club="ClubB"),
            _row(native_key=1, club="ClubA"),
        ]
    )
    assert characters[0]["records"] == [
        {"native_key": 1, "shape": 3, "club": "ClubA", "spine": "Spine_A", "avatar": "Avatar_A"},
        {"native_key": 2, "shape": 3, "club": "ClubB", "spine": "Spine_A", "avatar": "Avatar_A"},
    ]
    assert "club" not in characters[0]


def test_second_record_with_spine_makes_spine_available():
    characters = normalize_character_rows(
        [
            _row(native_key=1, spine=""),
            _row(native_key=2, spine="Spine_B"),
        ]
    )
    assert characters[0]["spine_available"] is True


def test_same_identifier_with_different_display_name_fails():
    with pytest.raises(AaOfficialDataError, match="多个不同官方显示名称"):
        normalize_character_rows(
            [
                _row(identifier="same", name="星野"),
                _row(identifier="same", name="小鸟"),
            ]
        )


def test_same_display_name_for_multiple_identifiers_is_ambiguous_not_error():
    output = build_official_character_data(
        rows=[
            _row(identifier="id-a", name="店員", native_key=1),
            _row(identifier="id-b", name="店員", native_key=2),
        ],
        source=_source(),
    )
    assert output["name_index"] == {"店員": ["id-a", "id-b"]}
    assert output["ambiguous_names"] == {"店員": ["id-a", "id-b"]}


def test_placeholder_identifier_records_stay_unresolved_and_out_of_name_index():
    output = build_official_character_data(
        rows=[
            {
                "id": "???",
                "name": "???",
                "native_key": 2746145574,
                "shape": 3,
                "club": "",
                "spine": "",
                "avatar": "UIs/01_Common/01_Character/NPC_Portrait_Null",
            },
            {
                "id": "???",
                "name": "？？？",
                "native_key": 901123296,
                "shape": 3,
                "club": "",
                "spine": "UIs/03_Scenario/02_Character/CharacterSpine_CH0228",
                "avatar": "UIs/01_Common/01_Character/Student_Portrait_CH0228",
            },
        ],
        source=_source(),
    )

    assert output["characters"] == []
    assert output["name_index"] == {}
    assert output["ambiguous_names"] == {}
    assert output["unresolved_records"] == [
        {
            "id": "???",
            "name": "？？？",
            "native_key": 901123296,
            "shape": 3,
            "club": "",
            "spine": "UIs/03_Scenario/02_Character/CharacterSpine_CH0228",
            "avatar": "UIs/01_Common/01_Character/Student_Portrait_CH0228",
        },
        {
            "id": "???",
            "name": "???",
            "native_key": 2746145574,
            "shape": 3,
            "club": "",
            "spine": "",
            "avatar": "UIs/01_Common/01_Character/NPC_Portrait_Null",
        },
    ]
    assert output["stats"]["unresolved_records"] == 2
    assert output["stats"]["records"] == 0


def test_output_is_stable_across_input_order():
    rows = [
        _row(identifier="b", name="乙", native_key=2, club="ClubB"),
        _row(identifier="a", name="甲", native_key=3, club="ClubC"),
        _row(identifier="a", name="甲", native_key=1, club="ClubA", spine="Spine_A"),
    ]
    output_a = build_official_character_data(rows=rows, source=_source())
    output_b = build_official_character_data(rows=list(reversed(copy.deepcopy(rows))), source=_source())
    assert output_a == output_b


def test_faces_remain_unknown_even_with_spine_and_avatar():
    characters = normalize_character_rows(
        [_row(spine="Spine_A", avatar="Avatar_A", native_key=1, shape=3)]
    )
    assert characters[0]["faces"] == []
    assert characters[0]["portrait_verified"] is False


def test_auto_cache_skips_cache_without_target_bundle(tmp_path):
    cache_a = _cache_dir(tmp_path, "cache-a")
    cache_b = _cache_dir(tmp_path, "cache-b")
    selected = resolve_character_bundle_from_discovered_caches(
        tmp_path / "catalog.json",
        [cache_a, cache_b],
        locator=_locator_for({"cache-b": "bundle-b"}),
    )
    assert selected[0] == cache_b
    assert selected[1] == cache_b / "bundle-b" / "hash-b" / "__data"


def test_auto_cache_fails_when_multiple_caches_are_valid(tmp_path):
    cache_a = _cache_dir(tmp_path, "cache-a")
    cache_b = _cache_dir(tmp_path, "cache-b")
    with pytest.raises(CharacterBundleAmbiguousError, match="显式指定 --cache"):
        resolve_character_bundle_from_discovered_caches(
            tmp_path / "catalog.json",
            [cache_a, cache_b],
            locator=_locator_for({"cache-a": "bundle-a", "cache-b": "bundle-b"}),
        )


def test_explicit_cache_does_not_fallback_to_discovered_cache(tmp_path):
    cache_a = _cache_dir(tmp_path, "cache-a")
    cache_b = _cache_dir(tmp_path, "cache-b")

    def discoverer(_aa_root):
        return [cache_b]

    with pytest.raises(CharacterBundleNotFoundError):
        resolve_character_bundle_for_cli(
            catalog_path=tmp_path / "catalog.json",
            aa_root=tmp_path,
            explicit_cache=cache_a,
            locator=_locator_for({"cache-b": "bundle-b"}),
            discoverer=discoverer,
        )


def test_ambiguous_cache_candidate_is_not_silently_skipped(tmp_path):
    cache_a = _cache_dir(tmp_path, "cache-a")
    cache_b = _cache_dir(tmp_path, "cache-b")

    def locator(_catalog_path, cache_root):
        if cache_root == cache_a:
            raise CharacterBundleAmbiguousError("缓存内部存在多个目标 bundle")
        return cache_root / "bundle-b" / "hash-b" / "__data", "bundle-b", "catalog-b", "hash-b"

    with pytest.raises(CharacterBundleAmbiguousError, match="多个目标 bundle"):
        resolve_character_bundle_from_discovered_caches(
            tmp_path / "catalog.json",
            [cache_a, cache_b],
            locator=locator,
        )


def test_locate_character_bundle_fails_on_multiple_cache_hash_candidates(tmp_path):
    catalog = _catalog_for_bundle(tmp_path, "target_bundle", "catalog_hash")
    cache = tmp_path / "cache"
    for hash_name in ("cache_hash_a", "cache_hash_b"):
        data = cache / "target_bundle" / hash_name / "__data"
        data.parent.mkdir(parents=True)
        data.write_bytes(b"bundle")

    with pytest.raises(CharacterBundleAmbiguousError, match="多个缓存 hash 候选"):
        locate_character_bundle(catalog, cache)


def test_discover_cache_candidates_returns_all_cache_like_dirs(tmp_path):
    aa_root = tmp_path / "aa"
    _cache_dir(aa_root, "资源文件")
    _cache_dir(tmp_path, "资源文件")
    candidates = discover_cache_candidates(aa_root)
    assert candidates == sorted(candidates, key=lambda path: str(path).casefold())
    assert aa_root / "资源文件" in candidates
    assert tmp_path / "资源文件" in candidates


def _row(
    *,
    identifier: str = "momoi",
    name: str = "桃井",
    native_key: int = 1,
    shape: int = 3,
    spine: str = "Spine_A",
    avatar: str = "Avatar_A",
    club: str = "GameDev",
) -> dict:
    return {
        "id": identifier,
        "name": name,
        "club": club,
        "native_key": native_key,
        "shape": shape,
        "spine": spine,
        "avatar": avatar,
        "faces": [],
    }


def _source() -> dict:
    return {
        "catalog_sha256": "a" * 64,
        "bundle_name": "bundle",
        "bundle_catalog_hash": "catalog",
        "bundle_cache_hash": "cache",
        "bundle_sha256": "b" * 64,
    }


def _cache_dir(root, name):
    cache = root / name
    data = cache / "some_bundle" / "some_hash" / "__data"
    data.parent.mkdir(parents=True)
    data.write_bytes(b"bundle")
    return cache.resolve()


def _locator_for(valid: dict[str, str]):
    def locator(_catalog_path, cache_root):
        bundle = valid.get(cache_root.name)
        if bundle is None:
            raise CharacterBundleNotFoundError(str(cache_root))
        bundle_path = cache_root / bundle / f"hash-{cache_root.name[-1]}" / "__data"
        return bundle_path, bundle, f"catalog-{cache_root.name[-1]}", f"hash-{cache_root.name[-1]}"

    return locator


def _catalog_for_bundle(tmp_path, bundle_name: str, catalog_hash: str):
    options = json.dumps(
        {"m_BundleName": bundle_name, "m_Hash": catalog_hash},
        ensure_ascii=False,
    ).encode("utf-16-le")
    extra = struct.pack("<I", len(options)) + options
    rows = [
        (0, 0, 1, 0, 0, 0, 0),
        (1, 0, -1, 0, 0, 0, 0),
    ]
    entry_data = b"\x00\x00\x00\x00" + b"".join(struct.pack("<7i", *row) for row in rows)
    catalog = {
        "m_InternalIds": ["aa/scenariocharacternameexceltable.bytes"],
        "m_EntryDataString": base64.b64encode(entry_data).decode("ascii"),
        "m_ExtraDataString": base64.b64encode(extra).decode("ascii"),
    }
    path = tmp_path / "catalog.json"
    path.write_text(json.dumps(catalog), encoding="utf-8")
    return path
