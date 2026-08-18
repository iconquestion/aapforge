"""源文件规范化。"""

from __future__ import annotations

from typing import Any

from aapforge.ir.canonical import (
    AaBackgroundRef,
    AaBgmRef,
    AaSoundRef,
    AppearDirective,
    AssetBackgroundRef,
    AssetSoundRef,
    BgRef,
    BgmRef,
    CanonicalAsset,
    CanonicalAssets,
    CanonicalCastMember,
    CanonicalLine,
    CanonicalProject,
    CanonicalScene,
    CanonicalSource,
    EnterAppearDirective,
    EnterOp,
    ExitAppearDirective,
    ExitOp,
    LibraryBackgroundRef,
    LibraryBgmRef,
    LibrarySoundRef,
    MoveDirective,
    MoveOp,
    SetFaceOp,
    SilentBgmRef,
    SoundRef,
    StageOp,
    TransitionDirective,
)


def normalize_source(data: dict[str, Any], *, file: str | None = None) -> CanonicalSource:
    del file
    extra = {key: value for key, value in data.items() if key.startswith("x_")}
    return CanonicalSource(
        schema_version="1.0",
        project=_normalize_project(data["project"]),
        cast=_normalize_cast(data["cast"]),
        assets=_normalize_assets(data.get("assets", {})),
        scenes=tuple(_normalize_scene(scene) for scene in data["scenes"]),
        extensions=data.get("extensions"),
        extra=extra or None,
    )


def _normalize_project(project: dict[str, Any]) -> CanonicalProject:
    return CanonicalProject(
        name=project["name"].strip(),
        default_bg=_normalize_bg(project.get("default_bg", {"kind": "aa", "name": "BG_Black"})),
        default_bgm=_normalize_bgm(project.get("default_bgm", {"kind": "silent"})),
    )


def _normalize_cast(cast: dict[str, Any]) -> tuple[CanonicalCastMember, ...]:
    members: list[CanonicalCastMember] = []
    for key, member in cast.items():
        narrator = member.get("narrator", False)
        members.append(
            CanonicalCastMember(
                key=key,
                narrator=narrator,
                id=member.get("id"),
                name=member.get("name"),
                portrait=False if narrator else member.get("portrait", False),
            )
        )
    return tuple(members)


def _normalize_assets(assets: dict[str, Any]) -> CanonicalAssets:
    return CanonicalAssets(
        backgrounds=tuple(_normalize_asset(item) for item in assets.get("backgrounds", [])),
        sounds=tuple(_normalize_asset(item) for item in assets.get("sounds", [])),
    )


def _normalize_asset(asset: dict[str, Any]) -> CanonicalAsset:
    return CanonicalAsset(id=asset["id"], name=asset["name"], path=asset["path"])


def _normalize_scene(scene: dict[str, Any]) -> CanonicalScene:
    return CanonicalScene(
        id=scene["id"],
        title=scene.get("title"),
        bg=_normalize_bg(scene["bg"]) if "bg" in scene else None,
        bgm=_normalize_bgm(scene["bgm"]) if "bgm" in scene else None,
        transition=_normalize_transition(scene["transition"]) if "transition" in scene else None,
        place=scene.get("place"),
        lines=tuple(_normalize_line(line) for line in scene["lines"]),
    )


def _normalize_line(line: dict[str, Any]) -> CanonicalLine:
    return CanonicalLine(
        speaker=line["speaker"],
        text=line["text"],
        bg=_normalize_bg(line["bg"]) if "bg" in line else None,
        bgm=_normalize_bgm(line["bgm"]) if "bgm" in line else None,
        se=_normalize_sound(line["se"]) if "se" in line else None,
        transition=_normalize_transition(line["transition"]) if "transition" in line else None,
        wait=line.get("wait"),
        place=line.get("place"),
        face=_normalize_face(line["face"]) if "face" in line else None,
        slot=line.get("slot"),
        move=_normalize_move(line["move"]) if "move" in line else None,
        appear=_normalize_appear(line["appear"]) if "appear" in line else None,
        action=line.get("action"),
        emoticon=line.get("emoticon"),
        shape=line.get("shape"),
        highlight=tuple(_dedupe(line["highlight"])) if "highlight" in line else (),
        stage_ops=tuple(_normalize_stage_op(op) for op in line.get("stage_ops", [])),
    )


def _normalize_bg(value: Any) -> BgRef:
    if isinstance(value, str):
        return AaBackgroundRef(name=value)
    if value["kind"] == "aa":
        return AaBackgroundRef(name=value["name"])
    if value["kind"] == "library":
        return LibraryBackgroundRef(id=value["id"])
    return AssetBackgroundRef(id=value["id"])


def _normalize_sound(value: Any) -> SoundRef:
    if isinstance(value, str):
        return AaSoundRef(name=value)
    if value["kind"] == "aa":
        return AaSoundRef(name=value["name"])
    if value["kind"] == "library":
        return LibrarySoundRef(id=value["id"])
    return AssetSoundRef(id=value["id"])


def _normalize_bgm(value: Any) -> BgmRef:
    if value == 999 or value["kind"] == "silent":
        return SilentBgmRef()
    if value["kind"] == "aa":
        return AaBgmRef(id=value["id"])
    return LibraryBgmRef(id=value["id"])


def _normalize_transition(value: dict[str, Any]) -> TransitionDirective:
    return TransitionDirective(type=value["type"], duration=value["duration"])


def _normalize_move(value: dict[str, Any]) -> MoveDirective:
    return MoveDirective(from_slot=value["from"], to_slot=value["to"])


def _normalize_appear(value: dict[str, Any]) -> AppearDirective:
    if value["type"] == "enter":
        return EnterAppearDirective(from_=value["from"])
    return ExitAppearDirective(to=value["to"])


def _normalize_stage_op(op: dict[str, Any]) -> StageOp:
    if op["op"] == "enter":
        return EnterOp(
            actor=op["actor"],
            slot=op["slot"],
            from_=op.get("from", "center"),
            face=_normalize_face(op.get("face", "00")),
        )
    if op["op"] == "exit":
        return ExitOp(actor=op["actor"], slot=op["slot"], to=op.get("to", "center"))
    if op["op"] == "move":
        return MoveOp(actor=op["actor"], from_slot=op["from"], to_slot=op["to"])
    return SetFaceOp(actor=op["actor"], slot=op["slot"], face=_normalize_face(op["face"]))


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
