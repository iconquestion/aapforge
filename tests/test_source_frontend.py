from __future__ import annotations

import copy
import json

import pytest

from aapforge.input.diagnostics import SourceError
from aapforge.input.loader import load_source_text
from aapforge.ir.canonical import (
    AaBackgroundRef,
    AaSoundRef,
    CanonicalLine,
    CanonicalProject,
    CanonicalScene,
    CanonicalSource,
    EnterOp,
    ExitOp,
    MoveOp,
    SetFaceOp,
    SilentBgmRef,
)


def _source():
    return {
        "aapforge": {"schema_version": "1.0"},
        "project": {"name": "Smoke"},
        "cast": {"旁白": {"narrator": True}},
        "scenes": [{"id": "s1", "lines": [{"speaker": "旁白", "text": "Hello"}]}],
    }


def _load(data):
    return load_source_text(json.dumps(data, ensure_ascii=False)).to_dict()


def _load_ir(data):
    return load_source_text(json.dumps(data, ensure_ascii=False))


def _fails(data, code: str = "E_SCHEMA"):
    with pytest.raises(SourceError) as raised:
        _load(data)
    assert raised.value.diagnostic.code == code
    assert raised.value.diagnostic.json_path


def test_json_valid_success():
    result = _load(_source())
    assert result["project"]["name"] == "Smoke"


def test_json_invalid_fails():
    with pytest.raises(SourceError) as raised:
        load_source_text('{"a":', file="bad.aapforge.json")
    diag = raised.value.diagnostic
    assert diag.code == "E_JSON_PARSE"
    assert diag.line == 1
    assert diag.column
    assert diag.file == "bad.aapforge.json"


def test_jsonc_comments_trailing_comma_and_url_success():
    text = """
    {
      // 行注释
      "aapforge": {"schema_version": "1.0"},
      "project": {"name": "Smoke"},
      "cast": {"旁白": {"narrator": true}},
      "scenes": [{
        "id": "s1",
        "lines": [{"speaker": "旁白", "text": "https://example.com",},],
      }],
      /* 块注释 */
    }
    """
    result = load_source_text(text, jsonc=True).to_dict()
    assert result["scenes"][0]["lines"][0]["text"] == "https://example.com"


def test_jsonc_invalid_has_line_column():
    with pytest.raises(SourceError) as raised:
        load_source_text('{\n  "a": [\n}', jsonc=True)
    assert raised.value.diagnostic.code == "E_JSON_PARSE"
    assert raised.value.diagnostic.line == 3
    assert raised.value.diagnostic.column


def test_top_level_not_object_fails():
    with pytest.raises(SourceError) as raised:
        load_source_text("[]")
    assert raised.value.diagnostic.code == "E_SCHEMA"
    assert raised.value.diagnostic.json_path == "$"


@pytest.mark.parametrize("field", ["aapforge", "project", "cast", "scenes"])
def test_missing_required_top_level_field_fails(field):
    data = _source()
    del data[field]
    _fails(data)


def test_unknown_top_level_field_fails():
    data = _source()
    data["unknown"] = {}
    _fails(data)


def test_x_and_extensions_allowed():
    data = _source()
    data["x_note"] = {"keep": True}
    data["extensions"] = {"demo": True}
    result = _load(data)
    assert result["x_note"] == {"keep": True}
    assert result["extensions"] == {"demo": True}


def test_schema_version_success_and_other_version_fails():
    _load(_source())
    data = _source()
    data["aapforge"]["schema_version"] = "2.0"
    _fails(data, "E_SCHEMA_VERSION")


@pytest.mark.parametrize("name", ["", "bad:name", ".", "..", "CON"])
def test_project_invalid_name_fails(name):
    data = _source()
    data["project"]["name"] = name
    _fails(data)


def test_project_defaults_are_canonical():
    result = _load(_source())
    assert result["project"]["default_bg"] == {"kind": "aa", "name": "BG_Black"}
    assert result["project"]["default_bgm"] == {"kind": "silent"}


def test_resource_shorthand_becomes_canonical():
    data = _source()
    line = data["scenes"][0]["lines"][0]
    line["bg"] = "BG_GameDevRoom"
    line["se"] = "SE_Button_01"
    line["bgm"] = 999
    result = _load(data)
    line = result["scenes"][0]["lines"][0]
    assert line["bg"] == {"kind": "aa", "name": "BG_GameDevRoom"}
    assert line["se"] == {"kind": "aa", "name": "SE_Button_01"}
    assert line["bgm"] == {"kind": "silent"}


def test_resource_object_and_shorthand_produce_same_canonical_ir():
    shorthand = _source()
    shorthand["scenes"][0]["lines"][0]["bg"] = "BG_GameDevRoom"
    obj = _source()
    obj["scenes"][0]["lines"][0]["bg"] = {"kind": "aa", "name": "BG_GameDevRoom"}
    assert _load(shorthand) == _load(obj)


def test_bgm_999_and_silent_object_produce_same_canonical_ir():
    shorthand = _source()
    shorthand["scenes"][0]["lines"][0]["bgm"] = 999
    obj = _source()
    obj["scenes"][0]["lines"][0]["bgm"] = {"kind": "silent"}
    assert _load(shorthand) == _load(obj)


def test_bgm_unsupported_source_fails():
    data = _source()
    data["scenes"][0]["lines"][0]["bgm"] = {"kind": "asset", "type": "bgm", "id": "x"}
    _fails(data, "E_UNSUPPORTED_BGM_SOURCE")


def test_bgm_bare_number_other_than_999_fails():
    data = _source()
    data["scenes"][0]["lines"][0]["bgm"] = 123
    _fails(data)


def test_cast_narrator_and_portrait_default():
    data = _source()
    data["cast"]["桃井"] = {"portrait": True}
    data["cast"]["系统音"] = {}
    result = _load(data)
    assert result["cast"]["旁白"] == {"narrator": True}
    assert result["cast"]["桃井"]["portrait"] is True
    assert result["cast"]["系统音"]["portrait"] is False


def test_cast_narrator_conflicts_fail():
    data = _source()
    data["cast"]["旁白"] = {"narrator": True, "id": "Narrator"}
    _fails(data)
    data = _source()
    data["cast"]["旁白"] = {"narrator": True, "portrait": False}
    _fails(data)


def test_assets_structure_and_duplicate_id():
    data = _source()
    data["assets"] = {
        "backgrounds": [{"id": "night_room", "name": "Night", "path": "assets/night.png"}],
        "sounds": [{"id": "click", "name": "Click", "path": "assets/click.wav"}],
    }
    result = _load(data)
    assert result["assets"]["backgrounds"][0]["id"] == "night_room"
    data["assets"]["backgrounds"].append(copy.deepcopy(data["assets"]["backgrounds"][0]))
    _fails(data)


def test_assets_bgms_rejected():
    data = _source()
    data["assets"] = {"bgms": []}
    _fails(data)


def test_scenes_empty_duplicate_and_lines_empty_fail():
    data = _source()
    data["scenes"] = []
    _fails(data)
    data = _source()
    data["scenes"].append(copy.deepcopy(data["scenes"][0]))
    _fails(data)
    data = _source()
    data["scenes"][0]["lines"] = []
    _fails(data)


def test_line_empty_text_is_valid():
    data = _source()
    data["scenes"][0]["lines"][0]["text"] = ""
    result = _load(data)
    assert result["scenes"][0]["lines"][0]["text"] == ""


def test_line_slot_wait_face_and_highlight_normalization():
    data = _source()
    line = data["scenes"][0]["lines"][0]
    line["slot"] = 3
    line["wait"] = 10
    line["face"] = 3
    line["highlight"] = [1, 2, 1, 0, 2]
    result = _load(data)
    line = result["scenes"][0]["lines"][0]
    assert line["face"] == "03"
    assert line["highlight"] == [1, 2, 0]


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("slot", 0),
        ("wait", -1),
        ("highlight", [6]),
    ],
)
def test_line_invalid_ranges_fail(field, value):
    data = _source()
    data["scenes"][0]["lines"][0][field] = value
    _fails(data)


@pytest.mark.parametrize(
    "op",
    [
        {"op": "enter", "actor": "桃井", "slot": 3},
        {"op": "enter", "actor": "桃井", "slot": 3, "from": "left", "face": 7},
        {"op": "exit", "actor": "桃井", "slot": 3},
        {"op": "exit", "actor": "桃井", "slot": 3, "to": "right"},
        {"op": "move", "actor": "桃井", "from": 3, "to": 1},
        {"op": "set_face", "actor": "桃井", "slot": 3, "face": 7},
    ],
)
def test_stage_ops_valid(op):
    data = _source()
    data["scenes"][0]["lines"][0]["stage_ops"] = [op]
    result = _load(data)
    stage_op = result["scenes"][0]["lines"][0]["stage_ops"][0]
    if op["op"] == "enter" and "from" not in op:
        assert stage_op == {"op": "enter", "actor": "桃井", "slot": 3, "from": "center", "face": "00"}
    elif op["op"] == "enter":
        assert stage_op["face"] == "07"
    elif op["op"] == "exit" and "to" not in op:
        assert stage_op == {"op": "exit", "actor": "桃井", "slot": 3, "to": "center"}
    elif op["op"] == "set_face":
        assert stage_op["face"] == "07"
    else:
        assert stage_op["op"] == op["op"]


@pytest.mark.parametrize(
    "op",
    [
        {"op": "enter", "actor": "桃井"},
        {"op": "exit", "actor": "桃井"},
        {"op": "move", "actor": "桃井", "from": 3},
        {"op": "move", "actor": "桃井", "to": 1},
        {"op": "set_face", "actor": "桃井", "face": "00"},
    ],
)
def test_stage_ops_missing_field_fails(op):
    data = _source()
    data["scenes"][0]["lines"][0]["stage_ops"] = [op]
    _fails(data)


@pytest.mark.parametrize(
    "op",
    [
        {"op": "enter", "actor": "桃井", "slot": 3, "extra": True},
        {"op": "exit", "actor": "桃井", "slot": 3, "extra": True},
        {"op": "move", "actor": "桃井", "from": 3, "to": 1, "extra": True},
        {"op": "set_face", "actor": "桃井", "slot": 3, "face": "00", "extra": True},
    ],
)
def test_stage_ops_unknown_field_fails(op):
    data = _source()
    data["scenes"][0]["lines"][0]["stage_ops"] = [op]
    _fails(data)


@pytest.mark.parametrize("slot", [0, 6])
def test_stage_ops_slot_range_fails(slot):
    data = _source()
    data["scenes"][0]["lines"][0]["stage_ops"] = [{"op": "enter", "actor": "桃井", "slot": slot}]
    _fails(data)


def test_enter_defaults_are_equivalent_to_explicit_values():
    shorthand = _source()
    shorthand["scenes"][0]["lines"][0]["stage_ops"] = [{"op": "enter", "actor": "桃井", "slot": 3}]
    obj = _source()
    obj["scenes"][0]["lines"][0]["stage_ops"] = [
        {"op": "enter", "actor": "桃井", "slot": 3, "from": "center", "face": "00"}
    ]
    assert _load(shorthand) == _load(obj)


def test_exit_defaults_are_equivalent_to_explicit_values():
    shorthand = _source()
    shorthand["scenes"][0]["lines"][0]["stage_ops"] = [{"op": "exit", "actor": "桃井", "slot": 3}]
    obj = _source()
    obj["scenes"][0]["lines"][0]["stage_ops"] = [{"op": "exit", "actor": "桃井", "slot": 3, "to": "center"}]
    assert _load(shorthand) == _load(obj)


def test_face_integer_and_string_produce_same_canonical_ir():
    number = _source()
    number["scenes"][0]["lines"][0]["face"] = 3
    text = _source()
    text["scenes"][0]["lines"][0]["face"] = "03"
    assert _load(number) == _load(text)


def test_canonical_ir_has_strong_types():
    data = _source()
    line = data["scenes"][0]["lines"][0]
    line["bg"] = "BG_GameDevRoom"
    line["se"] = "SE_Button_01"
    line["bgm"] = 999
    line["stage_ops"] = [
        {"op": "enter", "actor": "桃井", "slot": 3},
        {"op": "exit", "actor": "桃井", "slot": 3},
        {"op": "move", "actor": "桃井", "from": 3, "to": 1},
        {"op": "set_face", "actor": "桃井", "slot": 1, "face": 7},
    ]
    source = _load_ir(data)
    assert isinstance(source, CanonicalSource)
    assert isinstance(source.project, CanonicalProject)
    assert isinstance(source.project.default_bg, AaBackgroundRef)
    assert isinstance(source.project.default_bgm, SilentBgmRef)
    assert isinstance(source.scenes[0], CanonicalScene)
    assert isinstance(source.scenes[0].lines[0], CanonicalLine)
    canonical_line = source.scenes[0].lines[0]
    assert isinstance(canonical_line.bg, AaBackgroundRef)
    assert isinstance(canonical_line.se, AaSoundRef)
    assert isinstance(canonical_line.bgm, SilentBgmRef)
    assert isinstance(canonical_line.stage_ops[0], EnterOp)
    assert isinstance(canonical_line.stage_ops[1], ExitOp)
    assert isinstance(canonical_line.stage_ops[2], MoveOp)
    assert isinstance(canonical_line.stage_ops[3], SetFaceOp)


def test_m1_does_not_resolve_unknown_actor_or_resource():
    data = _source()
    line = data["scenes"][0]["lines"][0]
    line["speaker"] = "完全不存在的角色"
    line["bg"] = {"kind": "aa", "name": "THIS_BACKGROUND_DOES_NOT_EXIST"}
    line["bgm"] = {"kind": "aa", "id": 123456789}
    line["stage_ops"] = [{"op": "move", "actor": "不存在的人", "from": 1, "to": 2}]
    result = _load(data)
    line = result["scenes"][0]["lines"][0]
    assert line["speaker"] == "完全不存在的角色"
    assert line["bg"]["name"] == "THIS_BACKGROUND_DOES_NOT_EXIST"
    assert line["bgm"] == {"kind": "aa", "id": 123456789}
    assert line["stage_ops"][0]["actor"] == "不存在的人"
