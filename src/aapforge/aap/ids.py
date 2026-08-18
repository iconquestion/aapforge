"""AAPForge v1 GUID contract.

These identifiers mirror the HaloCue rule AAPForge v1 has chosen to freeze.
They are not claimed to be a general AzureArchive protocol requirement.
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
