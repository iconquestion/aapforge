"""Validation-only checks for frozen `.aap` golden fixtures."""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Any

T_PROJ = "ProjectData, Assembly-CSharp"
T_NODES = "System.Collections.Generic.List`1[[NodeData, Assembly-CSharp]], mscorlib"
T_ENTRY = "EntryNodeData, Assembly-CSharp"
T_SNODE = "ScriptNodeData, Assembly-CSharp"
T_EXIT = "ExitNodeData, Assembly-CSharp"
T_SLIST = "System.Collections.Generic.List`1[[ScriptData, Assembly-CSharp]], mscorlib"
T_SCRIPT = "ScriptData, Assembly-CSharp"
T_CLIST = "System.Collections.Generic.List`1[[ScriptData+CharacterRecordData, Assembly-CSharp]], mscorlib"
T_CHAR = "ScriptData+CharacterRecordData, Assembly-CSharp"
T_GLIST = "System.Collections.Generic.List`1[[System.Guid, mscorlib]], mscorlib"
T_ILIST = "System.Collections.Generic.List`1[[System.Int32, mscorlib]], mscorlib"

SCRIPT_KEYS = [
    "$type",
    "text",
    "popup",
    "bgEffect",
    "bgName",
    "bgFriendlyName",
    "sound",
    "voice",
    "transition",
    "bgmId",
    "selectionGroup",
    "additionalPrompt",
    "characters",
    "speakerSlotNum",
    "highlightedSlotNums",
    "isDialogScript",
    "placeText",
]
CHAR_KEYS = [
    "$type",
    "name",
    "faceId",
    "startingPos",
    "endingPos",
    "emoticon",
    "action",
    "effect",
    "appear",
    "shapeOverride",
]
NODE_TYPES = {T_ENTRY, T_SNODE, T_EXIT}


class AAPContractError(ValueError):
    pass


def load_aap(path: str | Path) -> dict[str, Any]:
    raw = Path(path).read_bytes()
    if raw.startswith(b"\xef\xbb\xbf"):
        raise AAPContractError("AAP fixture must be UTF-8 without BOM")
    data = json.loads(raw.decode("utf-8"))
    validate_aap_contract(data)
    return data


def validate_aap_contract(project: dict[str, Any]) -> None:
    errors: list[str] = []
    if project.get("$type") != T_PROJ:
        errors.append("bad ProjectData $type")
    for key in ("ProjectName", "PreviewBgName", "PreviewHeader", "PreviewTitle", "nodes"):
        if key not in project:
            errors.append(f"missing ProjectData.{key}")
    nodes_box = project.get("nodes", {})
    if nodes_box.get("$type") != T_NODES:
        errors.append("bad nodes list $type")
    nodes = nodes_box.get("$values")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes must be a non-empty list")
        _raise(errors)
    guids = []
    for node in nodes:
        if node.get("$type") not in NODE_TYPES:
            errors.append(f"bad node $type: {node.get('$type')}")
        guid = node.get("Guid")
        if not _is_guid(guid):
            errors.append(f"bad node Guid: {guid}")
        else:
            guids.append(guid)
        conns = node.get("ConnectionsTo", {})
        if conns.get("$type") != T_GLIST or not isinstance(conns.get("$values"), list):
            errors.append("bad ConnectionsTo list")
    if len(guids) != len(set(guids)):
        errors.append("node Guid values must be unique")
    entries = [node for node in nodes if node.get("$type") == T_ENTRY]
    exits = [node for node in nodes if node.get("$type") == T_EXIT]
    if len(entries) != 1:
        errors.append("there must be exactly one entry node")
    elif entries[0].get("Guid") != "00000000-0000-0000-0000-000000000000":
        errors.append("entry Guid must be all zeroes")
    if len(exits) != 1:
        errors.append("there must be exactly one exit node")
    guid_set = set(guids)
    for node in nodes:
        for target in node.get("ConnectionsTo", {}).get("$values", []):
            if target not in guid_set:
                errors.append(f"broken ConnectionsTo target: {target}")
    if entries:
        reachable = _reachable(nodes, entries[0]["Guid"])
        if guid_set - reachable:
            errors.append("node graph contains unreachable nodes")
    for script in _scripts(nodes):
        _validate_script(script, errors)
    _raise(errors)


def _validate_script(script: dict[str, Any], errors: list[str]) -> None:
    if list(script.keys()) != SCRIPT_KEYS:
        errors.append("ScriptData field order mismatch")
    if script.get("$type") != T_SCRIPT:
        errors.append("bad ScriptData $type")
    if script.get("selectionGroup") != 0:
        errors.append("selectionGroup must be 0")
    characters = script.get("characters", {})
    if characters.get("$type") != T_CLIST:
        errors.append("bad characters list $type")
    char_values = characters.get("$values")
    if not isinstance(char_values, list) or len(char_values) != 6:
        errors.append("characters length must be 6")
        char_values = []
    for character in char_values:
        if list(character.keys()) != CHAR_KEYS:
            errors.append("CharacterRecordData field order mismatch")
        if character.get("$type") != T_CHAR:
            errors.append("bad CharacterRecordData $type")
    speaker = script.get("speakerSlotNum")
    if not isinstance(speaker, int) or not 0 <= speaker <= 5:
        errors.append("speakerSlotNum must be 0..5")
    highlighted = script.get("highlightedSlotNums", {})
    if highlighted.get("$type") != T_ILIST:
        errors.append("bad highlightedSlotNums list $type")
    values = highlighted.get("$values")
    if not isinstance(values, list) or any(not isinstance(item, int) or not 0 <= item <= 5 for item in values):
        errors.append("highlightedSlotNums values must be 0..5")


def _scripts(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    scripts: list[dict[str, Any]] = []
    for node in nodes:
        if node.get("$type") == T_SNODE:
            boxed = node.get("Scripts", {})
            if boxed.get("$type") == T_SLIST and isinstance(boxed.get("$values"), list):
                scripts.extend(boxed["$values"])
        if node.get("$type") == T_EXIT and isinstance(node.get("NeScriptDirty"), dict):
            scripts.append(node["NeScriptDirty"])
    return scripts


def _reachable(nodes: list[dict[str, Any]], start: str) -> set[str]:
    by_guid = {node["Guid"]: node for node in nodes if _is_guid(node.get("Guid"))}
    seen: set[str] = set()
    stack = [start]
    while stack:
        guid = stack.pop()
        if guid in seen:
            continue
        seen.add(guid)
        node = by_guid.get(guid)
        if node is None:
            continue
        stack.extend(node.get("ConnectionsTo", {}).get("$values", []))
    return seen


def _is_guid(value: object) -> bool:
    if not isinstance(value, str):
        return False
    try:
        uuid.UUID(value)
    except ValueError:
        return False
    return True


def _raise(errors: list[str]) -> None:
    if errors:
        raise AAPContractError("; ".join(errors))
