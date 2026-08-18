"""只用于校验冻结 `.aap` 黄金样例的契约检查。"""

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
        raise AAPContractError("AAP 样例必须是无 BOM 的 UTF-8")
    data = json.loads(raw.decode("utf-8"))
    validate_aap_contract(data)
    return data


def validate_aap_contract(project: dict[str, Any]) -> None:
    errors: list[str] = []
    if project.get("$type") != T_PROJ:
        errors.append("ProjectData 的 $type 不正确")
    for key in ("ProjectName", "PreviewBgName", "PreviewHeader", "PreviewTitle", "nodes"):
        if key not in project:
            errors.append(f"缺少 ProjectData.{key}")
    nodes_box = project.get("nodes", {})
    if nodes_box.get("$type") != T_NODES:
        errors.append("节点列表的 $type 不正确")
    nodes = nodes_box.get("$values")
    if not isinstance(nodes, list) or not nodes:
        errors.append("nodes 必须是非空列表")
        _raise(errors)
    guids = []
    for node in nodes:
        if node.get("$type") not in NODE_TYPES:
            errors.append(f"节点 $type 不正确：{node.get('$type')}")
        guid = node.get("Guid")
        if not _is_guid(guid):
            errors.append(f"节点 Guid 不正确：{guid}")
        else:
            guids.append(guid)
        conns = node.get("ConnectionsTo", {})
        if conns.get("$type") != T_GLIST or not isinstance(conns.get("$values"), list):
            errors.append("ConnectionsTo 列表不正确")
    if len(guids) != len(set(guids)):
        errors.append("节点 Guid 值必须唯一")
    entries = [node for node in nodes if node.get("$type") == T_ENTRY]
    exits = [node for node in nodes if node.get("$type") == T_EXIT]
    if len(entries) != 1:
        errors.append("必须且只能有一个入口节点")
    elif entries[0].get("Guid") != "00000000-0000-0000-0000-000000000000":
        errors.append("入口节点 Guid 必须全为 0")
    if len(exits) != 1:
        errors.append("必须且只能有一个出口节点")
    guid_set = set(guids)
    for node in nodes:
        for target in node.get("ConnectionsTo", {}).get("$values", []):
            if target not in guid_set:
                errors.append(f"ConnectionsTo 指向不存在的目标：{target}")
    if entries:
        reachable = _reachable(nodes, entries[0]["Guid"])
        if guid_set - reachable:
            errors.append("节点图包含入口不可达节点")
    for script in _scripts(nodes):
        _validate_script(script, errors)
    _raise(errors)


def _validate_script(script: dict[str, Any], errors: list[str]) -> None:
    if list(script.keys()) != SCRIPT_KEYS:
        errors.append("ScriptData 字段顺序不匹配")
    if script.get("$type") != T_SCRIPT:
        errors.append("ScriptData 的 $type 不正确")
    if script.get("selectionGroup") != 0:
        errors.append("selectionGroup 必须是 0")
    characters = script.get("characters", {})
    if characters.get("$type") != T_CLIST:
        errors.append("characters 列表的 $type 不正确")
    char_values = characters.get("$values")
    if not isinstance(char_values, list) or len(char_values) != 6:
        errors.append("characters 长度必须是 6")
        char_values = []
    for character in char_values:
        if list(character.keys()) != CHAR_KEYS:
            errors.append("CharacterRecordData 字段顺序不匹配")
        if character.get("$type") != T_CHAR:
            errors.append("CharacterRecordData 的 $type 不正确")
    speaker = script.get("speakerSlotNum")
    if not isinstance(speaker, int) or not 0 <= speaker <= 5:
        errors.append("speakerSlotNum 必须在 0..5 范围内")
    highlighted = script.get("highlightedSlotNums", {})
    if highlighted.get("$type") != T_ILIST:
        errors.append("highlightedSlotNums 列表的 $type 不正确")
    values = highlighted.get("$values")
    if not isinstance(values, list) or any(not isinstance(item, int) or not 0 <= item <= 5 for item in values):
        errors.append("highlightedSlotNums 的值必须在 0..5 范围内")


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
