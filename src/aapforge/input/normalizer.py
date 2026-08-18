"""源文件规范化。"""

from __future__ import annotations

from typing import Any

from aapforge.ir.canonical import CanonicalSource


def normalize_source(data: dict[str, Any], *, file: str | None = None) -> CanonicalSource:
    del file
    out: dict[str, Any] = {
        "aapforge": {"schema_version": "1.0"},
        "project": _normalize_project(data["project"]),
        "cast": _normalize_cast(data["cast"]),
        "assets": _normalize_assets(data.get("assets", {})),
        "scenes": [_normalize_scene(scene) for scene in data["scenes"]],
    }
    if "extensions" in data:
        out["extensions"] = data["extensions"]
    for key, value in data.items():
        if key.startswith("x_"):
            out[key] = value
    return CanonicalSource(out)


def _normalize_project(project: dict[str, Any]) -> dict[str, Any]:
    out = {"name": project["name"].strip()}
    out["default_bg"] = _normalize_bg(project.get("default_bg", {"kind": "aa", "name": "BG_Black"}))
    out["default_bgm"] = _normalize_bgm(project.get("default_bgm", {"kind": "silent"}))
    return out


def _normalize_cast(cast: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for key, member in cast.items():
        if member.get("narrator", False):
            out[key] = {"narrator": True}
            continue
        row: dict[str, Any] = {"narrator": False, "portrait": member.get("portrait", False)}
        for field in ("id", "name"):
            if field in member:
                row[field] = member[field]
        out[key] = row
    return out


def _normalize_assets(assets: dict[str, Any]) -> dict[str, Any]:
    return {
        "backgrounds": [dict(item) for item in assets.get("backgrounds", [])],
        "sounds": [dict(item) for item in assets.get("sounds", [])],
    }


def _normalize_scene(scene: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": scene["id"],
        "lines": [_normalize_line(line) for line in scene["lines"]],
    }
    for field in ("title", "place"):
        if field in scene:
            out[field] = scene[field]
    if "bg" in scene:
        out["bg"] = _normalize_bg(scene["bg"])
    if "bgm" in scene:
        out["bgm"] = _normalize_bgm(scene["bgm"])
    if "transition" in scene:
        out["transition"] = dict(scene["transition"])
    return out


def _normalize_line(line: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {"speaker": line["speaker"], "text": line["text"]}
    if "bg" in line:
        out["bg"] = _normalize_bg(line["bg"])
    if "bgm" in line:
        out["bgm"] = _normalize_bgm(line["bgm"])
    if "se" in line:
        out["se"] = _normalize_sound(line["se"])
    for field in ("transition", "move", "appear"):
        if field in line:
            out[field] = dict(line[field])
    for field in ("wait", "place", "slot", "action", "emoticon", "shape"):
        if field in line:
            out[field] = line[field]
    if "face" in line:
        out["face"] = _normalize_face(line["face"])
    if "highlight" in line:
        out["highlight"] = _dedupe(line["highlight"])
    if "stage_ops" in line:
        out["stage_ops"] = [_normalize_stage_op(op) for op in line["stage_ops"]]
    return out


def _normalize_stage_op(op: dict[str, Any]) -> dict[str, Any]:
    out = dict(op)
    if out.get("op") == "set_face":
        out["face"] = _normalize_face(out["face"])
    return out


def _normalize_bg(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"kind": "aa", "name": value}
    return dict(value)


def _normalize_sound(value: Any) -> dict[str, Any]:
    if isinstance(value, str):
        return {"kind": "aa", "name": value}
    return dict(value)


def _normalize_bgm(value: Any) -> dict[str, Any]:
    if value == 999:
        return {"kind": "silent"}
    return dict(value)


def _normalize_face(value: str | int) -> str:
    if isinstance(value, int):
        return f"{value:02d}"
    return value


def _dedupe(values: list[int]) -> list[int]:
    seen: set[int] = set()
    out: list[int] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        out.append(value)
    return out
