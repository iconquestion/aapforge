from __future__ import annotations

import copy

import pytest

from aapforge.data.aa_official import (
    AaOfficialDataError,
    build_official_character_data,
    normalize_character_rows,
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
        {"native_key": 1, "shape": 3, "spine": "Spine_A", "avatar": "Avatar_A"},
        {"native_key": 2, "shape": 4, "spine": "Spine_B", "avatar": "Avatar_B"},
    ]
    assert "variant_native_keys" not in characters[0]


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


def test_output_is_stable_across_input_order():
    rows = [
        _row(identifier="b", name="乙", native_key=2),
        _row(identifier="a", name="甲", native_key=3),
        _row(identifier="a", name="甲", native_key=1, spine="Spine_A"),
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


def _row(
    *,
    identifier: str = "momoi",
    name: str = "桃井",
    native_key: int = 1,
    shape: int = 3,
    spine: str = "Spine_A",
    avatar: str = "Avatar_A",
) -> dict:
    return {
        "id": identifier,
        "name": name,
        "club": "GameDev",
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
        "bundle_content_hash": "content",
        "bundle_sha256": "b" * 64,
    }
