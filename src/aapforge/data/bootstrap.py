"""从 HaloCue 离线索引生成 AAPForge 核心数据候选。"""

from __future__ import annotations

from copy import deepcopy
from typing import Any

from aapforge.aap.hash import background_hash
from aapforge.data.tables import load_core_tables

PROVENANCE_KINDS = {"official", "observed", "derived"}
OFFICIAL_CHARACTER_SOURCE = "official_flatdata"


class BootstrapError(ValueError):
    """HaloCue 离线索引无法安全转换时抛出的错误。"""

    def __init__(self, code: str, message: str):
        super().__init__(f"{code}: {message}")
        self.code = code


def build_core_candidate(
    halocue_index: dict[str, Any],
    allowlist: dict[str, Any],
    *,
    tables_path: str | None = None,
) -> dict[str, Any]:
    """按白名单从 HaloCue 离线索引构造核心数据候选。"""

    _assert_mapping(halocue_index, "HaloCue 索引")
    _assert_mapping(allowlist, "白名单")
    _reject_bg_conflicts(halocue_index)
    if tables_path is not None:
        _cross_check_enums(halocue_index.get("enums", {}), load_core_tables(tables_path))

    backgrounds = _build_backgrounds(halocue_index, _require_string_list(allowlist, "backgrounds"))
    characters = _build_characters(halocue_index, allowlist)

    return {
        "schema_version": "1.0",
        "backgrounds": backgrounds,
        "sounds": [],
        "bgms": [],
        "characters": characters,
    }


def _build_backgrounds(data: dict[str, Any], names: list[str]) -> list[dict[str, Any]]:
    source_bg = data.get("bg")
    _assert_mapping(source_bg, "HaloCue bg")
    backgrounds = []
    for name in names:
        if name not in source_bg:
            raise BootstrapError("E_BOOTSTRAP_ALLOWLIST_MISSING_BG", f"白名单背景不存在：{name}")
        observed_hash = source_bg[name]
        if not isinstance(observed_hash, int):
            raise BootstrapError("E_BOOTSTRAP_BAD_BG_HASH", f"背景哈希必须是整数：{name}")
        expected_hash = background_hash(name)
        if observed_hash != expected_hash:
            raise BootstrapError(
                "E_BOOTSTRAP_BACKGROUND_HASH_CONFLICT",
                f"背景哈希冲突：{name} HaloCue={observed_hash} AAPForge={expected_hash}",
            )
        backgrounds.append(
            {
                "name": name,
                "hash": observed_hash,
                "evidence": [
                    {"field": "name", "kind": "observed", "source": "halocue:bg"},
                    {
                        "field": "hash",
                        "kind": "derived",
                        "source": "aapforge:background_hash",
                    },
                ],
            }
        )
    return sorted(backgrounds, key=lambda item: item["name"])


def _build_characters(data: dict[str, Any], allowlist: dict[str, Any]) -> list[dict[str, Any]]:
    wanted_names = _require_string_list(allowlist, "characters")
    wanted_faces = allowlist.get("faces", {})
    _assert_mapping(wanted_faces, "白名单 faces")
    source_characters = data.get("characters")
    _assert_list(source_characters, "HaloCue characters")
    result = []
    for name in wanted_names:
        rows = [row for row in source_characters if isinstance(row, dict) and row.get("name") == name]
        if not rows:
            raise BootstrapError("E_BOOTSTRAP_ALLOWLIST_MISSING_CHARACTER", f"白名单角色不存在：{name}")
        if len(rows) != 1:
            raise BootstrapError("E_BOOTSTRAP_AMBIGUOUS_CHARACTER", f"角色名称不唯一：{name}")
        row = rows[0]
        if row.get("source") != OFFICIAL_CHARACTER_SOURCE:
            raise BootstrapError(
                "E_BOOTSTRAP_UNOFFICIAL_CHARACTER",
                f"角色不是可确认的官方条目：{name}",
            )
        identifier = row.get("identifier")
        if not _non_empty_string(identifier):
            raise BootstrapError("E_BOOTSTRAP_BAD_CHARACTER", f"角色缺少官方标识：{name}")
        face_ids = _require_string_list(wanted_faces, name)
        result.append(_build_character(data, row, face_ids))
    return sorted(result, key=lambda item: item["id"])


def _build_character(data: dict[str, Any], row: dict[str, Any], face_ids: list[str]) -> dict[str, Any]:
    identifier = str(row["identifier"])
    _reject_ambiguous_variants(data, identifier)
    observed_faces = _observed_faces_for(data, identifier)
    faces = []
    for face_id in face_ids:
        if face_id not in observed_faces:
            _reject_candidate_only_face(data, identifier, face_id)
            raise BootstrapError(
                "E_BOOTSTRAP_ALLOWLIST_MISSING_FACE",
                f"角色 {row['name']} 缺少已观察表情：{face_id}",
            )
        face = observed_faces[face_id]
        faces.append(
            {
                "id": face_id,
                "label": str(face.get("label") or ""),
                "evidence": [
                    {
                        "field": "id",
                        "kind": "observed",
                        "source": "halocue:faces_used",
                    }
                ],
            }
        )
    faces.sort(key=lambda item: item["id"])
    return {
        "id": identifier,
        "canonical_name": str(row["name"]),
        "name": str(row["name"]),
        "aliases": [],
        "portrait_verified": bool(faces),
        "spine_available": True,
        "faces": faces,
        "evidence": [
            {
                "field": "id",
                "kind": "official",
                "source": "halocue:official_flatdata",
            },
            {
                "field": "name",
                "kind": "official",
                "source": "halocue:official_flatdata",
            },
            {
                "field": "faces",
                "kind": "observed",
                "source": "halocue:faces_used",
            },
        ],
    }


def _reject_ambiguous_variants(data: dict[str, Any], identifier: str) -> None:
    capabilities = data.get("face_capabilities", {})
    _assert_mapping(capabilities, "HaloCue face_capabilities")
    variants = capabilities.get(identifier, [])
    _assert_list(variants, f"HaloCue face_capabilities.{identifier}")
    if len(variants) > 1:
        raise BootstrapError(
            "E_BOOTSTRAP_AMBIGUOUS_VARIANT",
            f"角色存在多个立绘变体，不能自动冻结：{identifier}",
        )


def _observed_faces_for(data: dict[str, Any], identifier: str) -> dict[str, dict[str, Any]]:
    faces_used = data.get("faces_used", {})
    _assert_mapping(faces_used, "HaloCue faces_used")
    faces = faces_used.get(identifier, [])
    _assert_list(faces, f"HaloCue faces_used.{identifier}")
    out: dict[str, dict[str, Any]] = {}
    for face in faces:
        if not isinstance(face, dict) or not _non_empty_string(face.get("id")):
            raise BootstrapError("E_BOOTSTRAP_BAD_FACE", f"表情记录不合法：{identifier}")
        face_id = str(face["id"])
        if face_id in out:
            raise BootstrapError("E_BOOTSTRAP_DUPLICATE_FACE", f"表情编号重复：{identifier}/{face_id}")
        out[face_id] = deepcopy(face)
    return out


def _reject_candidate_only_face(data: dict[str, Any], identifier: str, face_id: str) -> None:
    capabilities = data.get("face_capabilities", {})
    _assert_mapping(capabilities, "HaloCue face_capabilities")
    for variant in capabilities.get(identifier, []):
        if not isinstance(variant, dict):
            continue
        for face in variant.get("faces", []):
            if not isinstance(face, dict) or str(face.get("id")) != face_id:
                continue
            sources = face.get("sources", [])
            if sources == ["atlas_candidate"] or "aap_observed" not in sources:
                raise BootstrapError(
                    "E_BOOTSTRAP_FACE_NOT_OBSERVED",
                    f"表情只有候选证据，缺少工程观察：{identifier}/{face_id}",
                )


def _reject_bg_conflicts(data: dict[str, Any]) -> None:
    conflicts = data.get("bg_conflict", [])
    _assert_list(conflicts, "HaloCue bg_conflict")
    if conflicts:
        raise BootstrapError(
            "E_BOOTSTRAP_BG_CONFLICT",
            "HaloCue 报告了同名背景冲突，不能生成候选数据",
        )


def _cross_check_enums(source_enums: Any, tables: dict[str, Any]) -> None:
    _assert_mapping(source_enums, "HaloCue enums")
    enum_pairs = {
        "action": "actions",
        "appear": "appears",
        "shape": "shapes",
        "emoticon": "emoticons",
    }
    for source_key, table_key in enum_pairs.items():
        source_table = source_enums.get(source_key, {})
        _assert_mapping(source_table, f"HaloCue enums.{source_key}")
        expected = tables[table_key]
        for raw_id, payload in source_table.items():
            if not isinstance(payload, dict):
                raise BootstrapError("E_BOOTSTRAP_BAD_ENUM", f"枚举项不合法：{source_key}.{raw_id}")
            value = _enum_value(source_key, payload)
            if not value:
                continue
            expected_id = expected.get(value)
            if expected_id is None:
                raise BootstrapError("E_BOOTSTRAP_ENUM_CONFLICT", f"核心表缺少枚举：{source_key}.{value}")
            if str(expected_id) != str(raw_id):
                raise BootstrapError(
                    "E_BOOTSTRAP_ENUM_CONFLICT",
                    f"枚举编号冲突：{source_key}.{value}",
                )


def _enum_value(source_key: str, payload: dict[str, Any]) -> str:
    key = "sym" if source_key == "emoticon" else "verb"
    value = payload.get(key)
    return value if isinstance(value, str) else ""


def _require_string_list(data: dict[str, Any], key: str) -> list[str]:
    values = data.get(key)
    _assert_list(values, key)
    if any(not _non_empty_string(value) for value in values):
        raise BootstrapError("E_BOOTSTRAP_BAD_ALLOWLIST", f"{key} 必须是非空字符串数组")
    if len(set(values)) != len(values):
        raise BootstrapError("E_BOOTSTRAP_BAD_ALLOWLIST", f"{key} 不允许重复")
    return [str(value) for value in values]


def _assert_mapping(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise BootstrapError("E_BOOTSTRAP_BAD_INPUT", f"{label} 必须是对象")


def _assert_list(value: Any, label: str) -> None:
    if not isinstance(value, list):
        raise BootstrapError("E_BOOTSTRAP_BAD_INPUT", f"{label} 必须是数组")


def _non_empty_string(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())
