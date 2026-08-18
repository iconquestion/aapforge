"""AAPForge v1 Guid 契约。

这些标识符遵循 AAPForge v1 选择冻结的 HaloCue 规则。
这里不声明它们是 AzureArchive 协议本身的通用要求。
"""

from __future__ import annotations

import uuid

NAMESPACE = uuid.UUID("6ba7b812-9dad-11d1-80b4-00c04fd430c8")
ENTRY_GUID = "00000000-0000-0000-0000-000000000000"


def scene_guid(project: str, index: int) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{project}/scene/{index}"))


def voice_guid(project: str, index: int) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{project}/voice/{index}"))


def exit_guid(project: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{project}/exit"))


def exit_voice_guid(project: str) -> str:
    return str(uuid.uuid5(NAMESPACE, f"{project}/exitvoice"))
