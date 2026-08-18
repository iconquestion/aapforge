from aapforge.aap.ids import ENTRY_GUID, exit_guid, exit_voice_guid, scene_guid, voice_guid


def test_guid_contract_for_smoke_project():
    assert ENTRY_GUID == "00000000-0000-0000-0000-000000000000"
    assert scene_guid("Smoke", 0) == "e7812056-cfd7-5654-83dc-b312bec3f91f"
    assert voice_guid("Smoke", 0) == "87057a17-30b6-5bd4-be80-15f2f9ad846a"
    assert exit_guid("Smoke") == "55e23095-0dd5-5cae-a061-e192a401851b"
    assert exit_voice_guid("Smoke") == "845ad67c-b6a8-5801-a6d8-3bb2b60d4d5a"
