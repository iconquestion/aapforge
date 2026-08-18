"""规范化 AA 官方角色表事实。"""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any


OFFICIAL_CHARACTER_TABLE = "ScenarioCharacterNameExcel"
OFFICIAL_EVIDENCE_SOURCE = "aa:ScenarioCharacterNameExcel"
PLACEHOLDER_CHARACTER_IDS = {"???"}


class AaOfficialDataError(ValueError):
    pass


def normalize_character_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """把官方表原始行规范化为 AAPForge 角色事实列表。"""

    if not isinstance(rows, list):
        raise AaOfficialDataError("官方角色原始记录必须是数组")
    if not rows:
        raise AaOfficialDataError("ScenarioCharacterNameExcel 没有有效角色记录")

    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for index, row in enumerate(rows):
        normalized = _normalize_row(row, index)
        if normalized["id"] in PLACEHOLDER_CHARACTER_IDS:
            continue
        grouped[normalized["id"]].append(normalized)

    if not grouped:
        return []

    characters = []
    for identifier in sorted(grouped):
        rows_for_id = sorted(
            grouped[identifier],
            key=lambda item: (
                item["native_key"],
                item["shape"],
                item["club"],
                item["spine"],
                item["avatar"],
            ),
        )
        names = {row["name"] for row in rows_for_id}
        if len(names) != 1:
            joined = ", ".join(sorted(names))
            raise AaOfficialDataError(
                f"同一个角色标识符对应多个不同官方显示名称：{identifier} -> {joined}"
            )
        name = rows_for_id[0]["name"]
        records = [
            {
                "native_key": row["native_key"],
                "shape": row["shape"],
                "club": row["club"],
                "spine": row["spine"],
                "avatar": row["avatar"],
            }
            for row in rows_for_id
        ]
        characters.append(
            {
                "id": identifier,
                "canonical_name": name,
                "name": name,
                "aliases": [],
                "spine_available": any(bool(record["spine"]) for record in records),
                "portrait_verified": False,
                "faces": [],
                "records": records,
                "evidence": [
                    {
                        "kind": "official",
                        "source": OFFICIAL_EVIDENCE_SOURCE,
                    }
                ],
            }
        )
    return characters


def build_unresolved_records(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """保留已知 placeholder identifier 的官方记录，但不构建稳定角色 identity。"""

    if not isinstance(rows, list):
        raise AaOfficialDataError("官方角色原始记录必须是数组")

    unresolved: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        normalized = _normalize_row(row, index)
        if normalized["id"] not in PLACEHOLDER_CHARACTER_IDS:
            continue
        unresolved.append(
            {
                "id": normalized["id"],
                "name": normalized["name"],
                "native_key": normalized["native_key"],
                "shape": normalized["shape"],
                "club": normalized["club"],
                "spine": normalized["spine"],
                "avatar": normalized["avatar"],
            }
        )

    return sorted(
        unresolved,
        key=lambda item: (
            item["native_key"],
            item["shape"],
            item["club"],
            item["spine"],
            item["avatar"],
            item["id"],
            item["name"],
        ),
    )


def build_name_index(characters: list[dict[str, Any]]) -> dict[str, list[str]]:
    index: dict[str, list[str]] = defaultdict(list)
    for character in characters:
        name = character["name"]
        index[name].append(character["id"])
    return {name: sorted(ids) for name, ids in sorted(index.items())}


def build_ambiguous_names(name_index: dict[str, list[str]]) -> dict[str, list[str]]:
    return {name: ids for name, ids in name_index.items() if len(ids) > 1}


def build_official_character_data(
    *,
    rows: list[dict[str, Any]],
    source: dict[str, Any],
) -> dict[str, Any]:
    """构建正式的 AA 官方角色事实数据。"""

    characters = normalize_character_rows(rows)
    unresolved_records = build_unresolved_records(rows)
    name_index = build_name_index(characters)
    ambiguous_names = build_ambiguous_names(name_index)
    records_count = sum(len(character["records"]) for character in characters)
    return {
        "schema_version": "1.0",
        "source": _normalize_source(source),
        "characters": characters,
        "unresolved_records": unresolved_records,
        "name_index": name_index,
        "ambiguous_names": ambiguous_names,
        "stats": {
            "characters": len(characters),
            "records": records_count,
            "names": len(name_index),
            "ambiguous_names": len(ambiguous_names),
            "unresolved_records": len(unresolved_records),
        },
    }


def _normalize_row(row: dict[str, Any], index: int) -> dict[str, Any]:
    if not isinstance(row, dict):
        raise AaOfficialDataError(f"官方角色第 {index} 行必须是对象")
    identifier = _require_string(row, "id", index)
    name = _require_string(row, "name", index)
    return {
        "id": identifier,
        "name": name,
        "native_key": _require_int(row, "native_key", index),
        "shape": _require_int(row, "shape", index),
        "club": _optional_string(row, "club", index),
        "spine": _optional_string(row, "spine", index),
        "avatar": _optional_string(row, "avatar", index),
    }


def _normalize_source(source: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise AaOfficialDataError("source 必须是对象")
    required = (
        "catalog_sha256",
        "bundle_name",
        "bundle_catalog_hash",
        "bundle_cache_hash",
        "bundle_sha256",
    )
    normalized = {
        "kind": "aa_official_flatdata",
        "table": OFFICIAL_CHARACTER_TABLE,
    }
    for key in required:
        value = source.get(key)
        if not isinstance(value, str) or not value.strip():
            raise AaOfficialDataError(f"source.{key} 必须是非空字符串")
        if _looks_like_local_path(value):
            raise AaOfficialDataError(f"source.{key} 不得包含本机路径")
        normalized[key] = value
    return normalized


def _require_string(row: dict[str, Any], key: str, index: int) -> str:
    value = row.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AaOfficialDataError(f"官方角色第 {index} 行 {key} 必须是非空字符串")
    if _looks_like_local_path(value):
        raise AaOfficialDataError(f"官方角色第 {index} 行 {key} 不得是本机路径")
    return value


def _optional_string(row: dict[str, Any], key: str, index: int) -> str:
    value = row.get(key, "")
    if not isinstance(value, str):
        raise AaOfficialDataError(f"官方角色第 {index} 行 {key} 必须是字符串")
    if _looks_like_local_path(value):
        raise AaOfficialDataError(f"官方角色第 {index} 行 {key} 不得是本机路径")
    return value


def _require_int(row: dict[str, Any], key: str, index: int) -> int:
    value = row.get(key)
    if not isinstance(value, int):
        raise AaOfficialDataError(f"官方角色第 {index} 行 {key} 必须是整数")
    return value


def _looks_like_local_path(value: str) -> bool:
    path = value.replace("\\", "/")
    if len(path) >= 3 and path[1] == ":" and path[2] == "/":
        return True
    return Path(value).is_absolute()
