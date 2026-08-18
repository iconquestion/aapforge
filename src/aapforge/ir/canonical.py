"""规范中间表示。

规范中间表示会消除默认值和兼容简写；后续阶段不需要再理解这些输入变体。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

Direction = Literal["left", "right", "center"]


@dataclass(frozen=True)
class AaBackgroundRef:
    name: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "aa", "name": self.name}


@dataclass(frozen=True)
class LibraryBackgroundRef:
    id: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "library", "type": "background", "id": self.id}


@dataclass(frozen=True)
class AssetBackgroundRef:
    id: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "asset", "type": "background", "id": self.id}


BgRef = AaBackgroundRef | LibraryBackgroundRef | AssetBackgroundRef


@dataclass(frozen=True)
class AaSoundRef:
    name: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "aa", "name": self.name}


@dataclass(frozen=True)
class LibrarySoundRef:
    id: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "library", "type": "sound", "id": self.id}


@dataclass(frozen=True)
class AssetSoundRef:
    id: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "asset", "type": "sound", "id": self.id}


SoundRef = AaSoundRef | LibrarySoundRef | AssetSoundRef


@dataclass(frozen=True)
class SilentBgmRef:
    def to_dict(self) -> dict[str, Any]:
        return {"kind": "silent"}


@dataclass(frozen=True)
class AaBgmRef:
    id: int

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "aa", "id": self.id}


@dataclass(frozen=True)
class LibraryBgmRef:
    id: str

    def to_dict(self) -> dict[str, Any]:
        return {"kind": "library", "type": "bgm", "id": self.id}


BgmRef = SilentBgmRef | AaBgmRef | LibraryBgmRef


@dataclass(frozen=True)
class TransitionDirective:
    type: str
    duration: int

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.type, "duration": self.duration}


@dataclass(frozen=True)
class MoveDirective:
    from_slot: int
    to_slot: int

    def to_dict(self) -> dict[str, Any]:
        return {"from": self.from_slot, "to": self.to_slot}


@dataclass(frozen=True)
class EnterAppearDirective:
    from_: Direction

    def to_dict(self) -> dict[str, Any]:
        return {"type": "enter", "from": self.from_}


@dataclass(frozen=True)
class ExitAppearDirective:
    to: Direction

    def to_dict(self) -> dict[str, Any]:
        return {"type": "exit", "to": self.to}


AppearDirective = EnterAppearDirective | ExitAppearDirective


@dataclass(frozen=True)
class EnterOp:
    actor: str
    slot: int
    from_: Direction
    face: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "op": "enter",
            "actor": self.actor,
            "slot": self.slot,
            "from": self.from_,
            "face": self.face,
        }


@dataclass(frozen=True)
class ExitOp:
    actor: str
    slot: int
    to: Direction

    def to_dict(self) -> dict[str, Any]:
        return {"op": "exit", "actor": self.actor, "slot": self.slot, "to": self.to}


@dataclass(frozen=True)
class MoveOp:
    actor: str
    from_slot: int
    to_slot: int

    def to_dict(self) -> dict[str, Any]:
        return {"op": "move", "actor": self.actor, "from": self.from_slot, "to": self.to_slot}


@dataclass(frozen=True)
class SetFaceOp:
    actor: str
    slot: int
    face: str

    def to_dict(self) -> dict[str, Any]:
        return {"op": "set_face", "actor": self.actor, "slot": self.slot, "face": self.face}


StageOp = EnterOp | ExitOp | MoveOp | SetFaceOp


@dataclass(frozen=True)
class CanonicalProject:
    name: str
    default_bg: BgRef
    default_bgm: BgmRef

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "default_bg": self.default_bg.to_dict(),
            "default_bgm": self.default_bgm.to_dict(),
        }


@dataclass(frozen=True)
class CanonicalCastMember:
    key: str
    narrator: bool
    id: str | None
    name: str | None
    portrait: bool

    def to_dict(self) -> dict[str, Any]:
        if self.narrator:
            return {"narrator": True}
        out: dict[str, Any] = {"narrator": False, "portrait": self.portrait}
        if self.id is not None:
            out["id"] = self.id
        if self.name is not None:
            out["name"] = self.name
        return out


@dataclass(frozen=True)
class CanonicalAsset:
    id: str
    name: str
    path: str

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "name": self.name, "path": self.path}


@dataclass(frozen=True)
class CanonicalAssets:
    backgrounds: tuple[CanonicalAsset, ...]
    sounds: tuple[CanonicalAsset, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "backgrounds": [item.to_dict() for item in self.backgrounds],
            "sounds": [item.to_dict() for item in self.sounds],
        }


@dataclass(frozen=True)
class CanonicalLine:
    speaker: str
    text: str
    bg: BgRef | None = None
    bgm: BgmRef | None = None
    se: SoundRef | None = None
    transition: TransitionDirective | None = None
    wait: int | None = None
    place: str | None = None
    face: str | None = None
    slot: int | None = None
    move: MoveDirective | None = None
    appear: AppearDirective | None = None
    action: str | int | None = None
    emoticon: str | int | None = None
    shape: str | int | None = None
    highlight: tuple[int, ...] = ()
    stage_ops: tuple[StageOp, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"speaker": self.speaker, "text": self.text}
        _maybe(out, "bg", self.bg)
        _maybe(out, "bgm", self.bgm)
        _maybe(out, "se", self.se)
        _maybe(out, "transition", self.transition)
        _maybe(out, "move", self.move)
        _maybe(out, "appear", self.appear)
        for key in ("wait", "place", "face", "slot", "action", "emoticon", "shape"):
            value = getattr(self, key)
            if value is not None:
                out[key] = value
        if self.highlight:
            out["highlight"] = list(self.highlight)
        if self.stage_ops:
            out["stage_ops"] = [op.to_dict() for op in self.stage_ops]
        return out


@dataclass(frozen=True)
class CanonicalScene:
    id: str
    lines: tuple[CanonicalLine, ...]
    title: str | None = None
    bg: BgRef | None = None
    bgm: BgmRef | None = None
    transition: TransitionDirective | None = None
    place: str | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {"id": self.id, "lines": [line.to_dict() for line in self.lines]}
        if self.title is not None:
            out["title"] = self.title
        _maybe(out, "bg", self.bg)
        _maybe(out, "bgm", self.bgm)
        _maybe(out, "transition", self.transition)
        if self.place is not None:
            out["place"] = self.place
        return out


@dataclass(frozen=True)
class CanonicalSource:
    schema_version: str
    project: CanonicalProject
    cast: tuple[CanonicalCastMember, ...]
    assets: CanonicalAssets
    scenes: tuple[CanonicalScene, ...]
    extensions: dict[str, Any] | None = None
    extra: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "aapforge": {"schema_version": self.schema_version},
            "project": self.project.to_dict(),
            "cast": {member.key: member.to_dict() for member in self.cast},
            "assets": self.assets.to_dict(),
            "scenes": [scene.to_dict() for scene in self.scenes],
        }
        if self.extensions is not None:
            out["extensions"] = self.extensions
        if self.extra:
            out.update(self.extra)
        return out


def _maybe(out: dict[str, Any], key: str, value: Any) -> None:
    if value is not None:
        out[key] = value.to_dict()
