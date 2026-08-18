from __future__ import annotations

import copy
from pathlib import Path

import pytest

from aapforge.aap.contract import AAPContractError, load_aap, validate_aap_contract

ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "tests/golden/minimal_narrator.aap"


def _golden():
    return load_aap(GOLDEN)


def _first_dialog_script(data):
    return data["nodes"]["$values"][1]["Scripts"]["$values"][0]


def test_minimal_golden_passes():
    load_aap(GOLDEN)


def test_wrong_type_fails():
    data = _golden()
    data["$type"] = "Wrong"
    with pytest.raises(AAPContractError):
        validate_aap_contract(data)


def test_missing_node_fails():
    data = _golden()
    data["nodes"]["$values"] = data["nodes"]["$values"][:1]
    with pytest.raises(AAPContractError):
        validate_aap_contract(data)


def test_characters_not_six_fails():
    data = _golden()
    script = _first_dialog_script(data)
    script["characters"]["$values"] = script["characters"]["$values"][:5]
    with pytest.raises(AAPContractError):
        validate_aap_contract(data)


def test_bad_speaker_slot_fails():
    data = _golden()
    _first_dialog_script(data)["speakerSlotNum"] = 6
    with pytest.raises(AAPContractError):
        validate_aap_contract(data)


def test_selection_group_not_zero_fails():
    data = _golden()
    _first_dialog_script(data)["selectionGroup"] = 1
    with pytest.raises(AAPContractError):
        validate_aap_contract(data)


def test_broken_connections_to_fails():
    data = _golden()
    data["nodes"]["$values"][0]["ConnectionsTo"]["$values"] = [
        "11111111-1111-1111-1111-111111111111"
    ]
    with pytest.raises(AAPContractError):
        validate_aap_contract(data)


def test_script_field_order_fails():
    data = _golden()
    script = _first_dialog_script(data)
    reordered = copy.deepcopy(script)
    value = reordered.pop("text")
    reordered["text"] = value
    data["nodes"]["$values"][1]["Scripts"]["$values"][0] = reordered
    with pytest.raises(AAPContractError):
        validate_aap_contract(data)
