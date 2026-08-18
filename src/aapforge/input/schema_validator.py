"""源文件结构校验。"""

from __future__ import annotations

import re
from typing import Any

from aapforge.input.diagnostics import SourceDiagnostic, SourceError

ID_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_.-]*$")
WINDOWS_BAD = set('<>:"/\\|?*')
WINDOWS_RESERVED = {
    "CON",
    "PRN",
    "AUX",
    "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}


def validate_source_schema(data: Any, *, file: str | None = None) -> None:
    if not isinstance(data, dict):
        _fail("E_SCHEMA", "顶层必须是对象", file=file, path="$")
    _require_keys(data, ("aapforge", "project", "cast", "scenes"), file=file, path="$")
    _check_unknown(data, {"aapforge", "project", "cast", "assets", "scenes", "extensions"}, file=file, path="$", allow_x=True)
    _validate_aapforge(data["aapforge"], file=file)
    _validate_project(data["project"], file=file)
    _validate_cast(data["cast"], file=file)
    if "assets" in data:
        _validate_assets(data["assets"], file=file)
    if "scenes" not in data or not isinstance(data["scenes"], list) or not data["scenes"]:
        _fail("E_SCHEMA", "scenes 必须是非空数组", file=file, path="$.scenes")
    seen_scene_ids: set[str] = set()
    for index, scene in enumerate(data["scenes"]):
        _validate_scene(scene, index, seen_scene_ids, file=file)


def _validate_aapforge(value: Any, *, file: str | None) -> None:
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "aapforge 必须是对象", file=file, path="$.aapforge")
    _require_keys(value, ("schema_version",), file=file, path="$.aapforge")
    _check_unknown(value, {"schema_version"}, file=file, path="$.aapforge")
    if value.get("schema_version") != "1.0":
        _fail("E_SCHEMA_VERSION", "schema_version 必须是 1.0", file=file, path="$.aapforge.schema_version")


def _validate_project(value: Any, *, file: str | None) -> None:
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "project 必须是对象", file=file, path="$.project")
    _require_keys(value, ("name",), file=file, path="$.project")
    _check_unknown(value, {"name", "default_bg", "default_bgm"}, file=file, path="$.project")
    name = value.get("name")
    if not isinstance(name, str):
        _fail("E_SCHEMA", "project.name 必须是字符串", file=file, path="$.project.name")
    cleaned = name.strip()
    if not cleaned or len(cleaned) > 80:
        _fail("E_SCHEMA", "project.name 去除首尾空白后长度必须是 1..80", file=file, path="$.project.name")
    if cleaned in {".", ".."} or any(char in WINDOWS_BAD for char in cleaned):
        _fail("E_SCHEMA", "project.name 包含 Windows 文件名非法字符", file=file, path="$.project.name")
    stem = cleaned.split(".")[0].upper()
    if stem in WINDOWS_RESERVED:
        _fail("E_SCHEMA", "project.name 不得使用 Windows 保留设备名", file=file, path="$.project.name")
    if "default_bg" in value:
        _validate_bg_ref(value["default_bg"], file=file, path="$.project.default_bg")
    if "default_bgm" in value:
        _validate_bgm_ref(value["default_bgm"], file=file, path="$.project.default_bgm")


def _validate_cast(value: Any, *, file: str | None) -> None:
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "cast 必须是对象", file=file, path="$.cast")
    for key, member in value.items():
        path = f"$.cast.{key}"
        if not isinstance(key, str) or not key.strip():
            _fail("E_SCHEMA", "cast 键必须是非空字符串", file=file, path="$.cast")
        if not isinstance(member, dict):
            _fail("E_SCHEMA", "cast 成员必须是对象", file=file, path=path)
        _check_unknown(member, {"narrator", "id", "name", "portrait"}, file=file, path=path)
        narrator = member.get("narrator", False)
        if not isinstance(narrator, bool):
            _fail("E_SCHEMA", "narrator 必须是布尔值", file=file, path=f"{path}.narrator")
        if narrator and any(field in member for field in ("id", "portrait")):
            _fail("E_SCHEMA", "narrator=true 时不得同时出现 id 或 portrait", file=file, path=path)
        if "id" in member and not _non_empty_string(member["id"]):
            _fail("E_SCHEMA", "cast.id 必须是非空字符串", file=file, path=f"{path}.id")
        if "name" in member and not _non_empty_string(member["name"]):
            _fail("E_SCHEMA", "cast.name 必须是非空字符串", file=file, path=f"{path}.name")
        if "portrait" in member and not isinstance(member["portrait"], bool):
            _fail("E_SCHEMA", "portrait 必须是布尔值", file=file, path=f"{path}.portrait")


def _validate_assets(value: Any, *, file: str | None) -> None:
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "assets 必须是对象", file=file, path="$.assets")
    _check_unknown(value, {"backgrounds", "sounds"}, file=file, path="$.assets")
    for field in ("backgrounds", "sounds"):
        items = value.get(field, [])
        if not isinstance(items, list):
            _fail("E_SCHEMA", f"assets.{field} 必须是数组", file=file, path=f"$.assets.{field}")
        seen: set[str] = set()
        for index, item in enumerate(items):
            _validate_asset(item, file=file, path=f"$.assets.{field}[{index}]")
            if item["id"] in seen:
                _fail("E_SCHEMA", f"assets.{field} id 不得重复", file=file, path=f"$.assets.{field}[{index}].id")
            seen.add(item["id"])


def _validate_asset(value: Any, *, file: str | None, path: str) -> None:
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "asset 必须是对象", file=file, path=path)
    _require_keys(value, ("id", "name", "path"), file=file, path=path)
    _check_unknown(value, {"id", "name", "path"}, file=file, path=path)
    _validate_id(value.get("id"), file=file, path=f"{path}.id")
    for field in ("name", "path"):
        if not _non_empty_string(value.get(field)):
            _fail("E_SCHEMA", f"{field} 必须是非空字符串", file=file, path=f"{path}.{field}")


def _validate_scene(value: Any, index: int, seen_scene_ids: set[str], *, file: str | None) -> None:
    path = f"$.scenes[{index}]"
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "scene 必须是对象", file=file, path=path)
    _require_keys(value, ("id", "lines"), file=file, path=path)
    _check_unknown(value, {"id", "title", "bg", "bgm", "transition", "place", "lines"}, file=file, path=path)
    _validate_id(value.get("id"), file=file, path=f"{path}.id")
    if value["id"] in seen_scene_ids:
        _fail("E_SCHEMA", "scene.id 不得重复", file=file, path=f"{path}.id")
    seen_scene_ids.add(value["id"])
    for field in ("title", "place"):
        if field in value and not isinstance(value[field], str):
            _fail("E_SCHEMA", f"{field} 必须是字符串", file=file, path=f"{path}.{field}")
    if "bg" in value:
        _validate_bg_ref(value["bg"], file=file, path=f"{path}.bg")
    if "bgm" in value:
        _validate_bgm_ref(value["bgm"], file=file, path=f"{path}.bgm")
    if "transition" in value:
        _validate_transition(value["transition"], file=file, path=f"{path}.transition")
    if not isinstance(value.get("lines"), list) or not value["lines"]:
        _fail("E_SCHEMA", "lines 必须是非空数组", file=file, path=f"{path}.lines")
    for line_index, line in enumerate(value["lines"]):
        _validate_line(line, file=file, path=f"{path}.lines[{line_index}]")


def _validate_line(value: Any, *, file: str | None, path: str) -> None:
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "line 必须是对象", file=file, path=path)
    allowed = {
        "speaker",
        "text",
        "bg",
        "bgm",
        "transition",
        "se",
        "wait",
        "place",
        "face",
        "slot",
        "move",
        "appear",
        "action",
        "emoticon",
        "shape",
        "highlight",
        "stage_ops",
    }
    _require_keys(value, ("speaker", "text"), file=file, path=path)
    _check_unknown(value, allowed, file=file, path=path)
    if not _non_empty_string(value.get("speaker")):
        _fail("E_SCHEMA", "speaker 必须是非空字符串", file=file, path=f"{path}.speaker")
    if not isinstance(value.get("text"), str):
        _fail("E_SCHEMA", "text 必须是字符串", file=file, path=f"{path}.text")
    if "bg" in value:
        _validate_bg_ref(value["bg"], file=file, path=f"{path}.bg")
    if "bgm" in value:
        _validate_bgm_ref(value["bgm"], file=file, path=f"{path}.bgm")
    if "se" in value:
        _validate_sound_ref(value["se"], file=file, path=f"{path}.se")
    if "transition" in value:
        _validate_transition(value["transition"], file=file, path=f"{path}.transition")
    if "wait" in value:
        _validate_int_range(value["wait"], 0, 600000, file=file, path=f"{path}.wait")
    if "slot" in value:
        _validate_int_range(value["slot"], 1, 5, file=file, path=f"{path}.slot")
    if "face" in value:
        _validate_face(value["face"], file=file, path=f"{path}.face")
    if "highlight" in value:
        _validate_highlight(value["highlight"], file=file, path=f"{path}.highlight")
    if "move" in value:
        _validate_move(value["move"], file=file, path=f"{path}.move")
    if "appear" in value:
        _validate_appear(value["appear"], file=file, path=f"{path}.appear")
    if "stage_ops" in value:
        _validate_stage_ops(value["stage_ops"], file=file, path=f"{path}.stage_ops")
    for field in ("place", "action", "emoticon", "shape"):
        if field in value and not isinstance(value[field], (str, int)):
            _fail("E_SCHEMA", f"{field} 必须是字符串或整数", file=file, path=f"{path}.{field}")


def _validate_bg_ref(value: Any, *, file: str | None, path: str) -> None:
    _validate_named_ref(value, expected_type="background", file=file, path=path)


def _validate_sound_ref(value: Any, *, file: str | None, path: str) -> None:
    _validate_named_ref(value, expected_type="sound", file=file, path=path)


def _validate_named_ref(value: Any, *, expected_type: str, file: str | None, path: str) -> None:
    if isinstance(value, str):
        if not value.strip():
            _fail("E_SCHEMA", "资源简写必须是非空字符串", file=file, path=path)
        return
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "资源引用必须是对象或字符串简写", file=file, path=path)
    kind = value.get("kind")
    if kind == "aa":
        _require_keys(value, ("kind", "name"), file=file, path=path)
        _check_unknown(value, {"kind", "name"}, file=file, path=path)
        if not _non_empty_string(value.get("name")):
            _fail("E_SCHEMA", "AA 资源 name 必须是非空字符串", file=file, path=f"{path}.name")
        return
    if kind in {"library", "asset"}:
        _require_keys(value, ("kind", "type", "id"), file=file, path=path)
        _check_unknown(value, {"kind", "type", "id"}, file=file, path=path)
        if value.get("type") != expected_type:
            _fail("E_SCHEMA", f"type 必须是 {expected_type}", file=file, path=f"{path}.type")
        _validate_id(value.get("id"), file=file, path=f"{path}.id")
        return
    _fail("E_SCHEMA", "资源 kind 不合法", file=file, path=f"{path}.kind")


def _validate_bgm_ref(value: Any, *, file: str | None, path: str) -> None:
    if isinstance(value, int):
        if value == 999:
            return
        _fail("E_SCHEMA", "背景音乐裸数字只允许 999", file=file, path=path)
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "背景音乐引用必须是对象或 999", file=file, path=path)
    kind = value.get("kind")
    if kind == "silent":
        _check_unknown(value, {"kind"}, file=file, path=path)
        return
    if kind == "aa":
        _require_keys(value, ("kind", "id"), file=file, path=path)
        _check_unknown(value, {"kind", "id"}, file=file, path=path)
        if not isinstance(value.get("id"), int):
            _fail("E_SCHEMA", "AA 背景音乐 id 必须是整数", file=file, path=f"{path}.id")
        return
    if kind == "library":
        _require_keys(value, ("kind", "type", "id"), file=file, path=path)
        _check_unknown(value, {"kind", "type", "id"}, file=file, path=path)
        if value.get("type") != "bgm":
            _fail("E_SCHEMA", "type 必须是 bgm", file=file, path=f"{path}.type")
        _validate_id(value.get("id"), file=file, path=f"{path}.id")
        return
    if kind in {"asset", "file"}:
        _fail("E_UNSUPPORTED_BGM_SOURCE", "当前源语言不支持这种背景音乐来源", file=file, path=f"{path}.kind")
    _fail("E_SCHEMA", "背景音乐 kind 不合法", file=file, path=f"{path}.kind")


def _validate_transition(value: Any, *, file: str | None, path: str) -> None:
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "transition 必须是对象", file=file, path=path)
    _require_keys(value, ("type", "duration"), file=file, path=path)
    _check_unknown(value, {"type", "duration"}, file=file, path=path)
    if not _non_empty_string(value.get("type")):
        _fail("E_SCHEMA", "transition.type 必须是非空字符串", file=file, path=f"{path}.type")
    _validate_int_range(value.get("duration"), 0, 600000, file=file, path=f"{path}.duration")


def _validate_move(value: Any, *, file: str | None, path: str) -> None:
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "move 必须是对象", file=file, path=path)
    _require_keys(value, ("from", "to"), file=file, path=path)
    _check_unknown(value, {"from", "to"}, file=file, path=path)
    _validate_int_range(value.get("from"), 1, 5, file=file, path=f"{path}.from")
    _validate_int_range(value.get("to"), 1, 5, file=file, path=f"{path}.to")


def _validate_appear(value: Any, *, file: str | None, path: str) -> None:
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "appear 必须是对象", file=file, path=path)
    kind = value.get("type")
    if kind == "enter":
        _require_keys(value, ("type", "from"), file=file, path=path)
        _check_unknown(value, {"type", "from"}, file=file, path=path)
        _validate_direction(value.get("from"), file=file, path=f"{path}.from")
        return
    if kind == "exit":
        _require_keys(value, ("type", "to"), file=file, path=path)
        _check_unknown(value, {"type", "to"}, file=file, path=path)
        _validate_direction(value.get("to"), file=file, path=f"{path}.to")
        return
    _fail("E_SCHEMA", "appear.type 必须是 enter 或 exit", file=file, path=f"{path}.type")


def _validate_stage_ops(value: Any, *, file: str | None, path: str) -> None:
    if not isinstance(value, list):
        _fail("E_SCHEMA", "stage_ops 必须是数组", file=file, path=path)
    for index, op in enumerate(value):
        _validate_stage_op(op, file=file, path=f"{path}[{index}]")


def _validate_stage_op(value: Any, *, file: str | None, path: str) -> None:
    if not isinstance(value, dict):
        _fail("E_SCHEMA", "stage_op 必须是对象", file=file, path=path)
    op = value.get("op")
    if op == "enter":
        _require_keys(value, ("op", "actor", "slot"), file=file, path=path)
        _check_unknown(value, {"op", "actor", "slot", "from", "face"}, file=file, path=path)
        _validate_actor(value.get("actor"), file=file, path=f"{path}.actor")
        _validate_int_range(value.get("slot"), 1, 5, file=file, path=f"{path}.slot")
        if "from" in value:
            _validate_direction(value["from"], file=file, path=f"{path}.from")
        if "face" in value:
            _validate_face(value["face"], file=file, path=f"{path}.face")
        return
    if op == "exit":
        _require_keys(value, ("op", "actor", "slot"), file=file, path=path)
        _check_unknown(value, {"op", "actor", "slot", "to"}, file=file, path=path)
        _validate_actor(value.get("actor"), file=file, path=f"{path}.actor")
        _validate_int_range(value.get("slot"), 1, 5, file=file, path=f"{path}.slot")
        if "to" in value:
            _validate_direction(value["to"], file=file, path=f"{path}.to")
        return
    if op == "move":
        _require_keys(value, ("op", "actor", "from", "to"), file=file, path=path)
        _check_unknown(value, {"op", "actor", "from", "to"}, file=file, path=path)
        _validate_actor(value.get("actor"), file=file, path=f"{path}.actor")
        _validate_int_range(value.get("from"), 1, 5, file=file, path=f"{path}.from")
        _validate_int_range(value.get("to"), 1, 5, file=file, path=f"{path}.to")
        return
    if op == "set_face":
        _require_keys(value, ("op", "actor", "slot", "face"), file=file, path=path)
        _check_unknown(value, {"op", "actor", "slot", "face"}, file=file, path=path)
        _validate_actor(value.get("actor"), file=file, path=f"{path}.actor")
        _validate_int_range(value.get("slot"), 1, 5, file=file, path=f"{path}.slot")
        _validate_face(value.get("face"), file=file, path=f"{path}.face")
        return
    _fail("E_SCHEMA", "stage_ops.op 不合法", file=file, path=f"{path}.op")


def _validate_actor(value: Any, *, file: str | None, path: str) -> None:
    if not _non_empty_string(value):
        _fail("E_SCHEMA", "actor 必须是非空字符串", file=file, path=path)


def _validate_face(value: Any, *, file: str | None, path: str) -> None:
    if isinstance(value, int):
        if value < 0:
            _fail("E_SCHEMA", "face 整数不得为负数", file=file, path=path)
        return
    if not _non_empty_string(value):
        _fail("E_SCHEMA", "face 必须是非空字符串或非负整数", file=file, path=path)


def _validate_highlight(value: Any, *, file: str | None, path: str) -> None:
    if not isinstance(value, list):
        _fail("E_SCHEMA", "highlight 必须是数组", file=file, path=path)
    for index, item in enumerate(value):
        _validate_int_range(item, 0, 5, file=file, path=f"{path}[{index}]")


def _validate_direction(value: Any, *, file: str | None, path: str) -> None:
    if value not in {"left", "right", "center"}:
        _fail("E_SCHEMA", "方向必须是 left、right 或 center", file=file, path=path)


def _validate_int_range(value: Any, low: int, high: int, *, file: str | None, path: str) -> None:
    if not isinstance(value, int) or not low <= value <= high:
        _fail("E_SCHEMA", f"必须是 {low}..{high} 范围内的整数", file=file, path=path)


def _validate_id(value: Any, *, file: str | None, path: str) -> None:
    if not isinstance(value, str) or not ID_RE.match(value):
        _fail("E_SCHEMA", "id 格式不合法", file=file, path=path)


def _require_keys(value: dict[str, Any], keys: tuple[str, ...], *, file: str | None, path: str) -> None:
    for key in keys:
        if key not in value:
            _fail("E_SCHEMA", f"缺少字段 {key}", file=file, path=path)


def _check_unknown(value: dict[str, Any], allowed: set[str], *, file: str | None, path: str, allow_x: bool = False) -> None:
    for key in value:
        if key in allowed or (allow_x and key.startswith("x_")):
            continue
        _fail("E_SCHEMA", f"未知字段 {key}", file=file, path=f"{path}.{key}")


def _non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _fail(code: str, message: str, *, file: str | None, path: str) -> None:
    raise SourceError(SourceDiagnostic(code=code, message=message, file=file, json_path=path))
