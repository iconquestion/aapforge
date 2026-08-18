from __future__ import annotations

from pathlib import Path

import pytest

from aapforge.data.tables import TableDataError, load_core_tables, validate_core_tables

ROOT = Path(__file__).resolve().parents[1]


def test_valid_tables_pass():
    load_core_tables(ROOT / "resources/core/tables.json")


def test_bad_enum_value_type_fails():
    data = load_core_tables(ROOT / "resources/core/tables.json")
    data["actions"]["jump"] = "6"
    with pytest.raises(TableDataError):
        validate_core_tables(data)


def test_bad_transition_key_fails():
    data = load_core_tables(ROOT / "resources/core/tables.json")
    data["transitions"]["Fade Maybe Later"] = 1
    with pytest.raises(TableDataError):
        validate_core_tables(data)


def test_bad_hash_contract_fails():
    data = load_core_tables(ROOT / "resources/core/tables.json")
    data["hashes"]["background"] = "sha256"
    with pytest.raises(TableDataError):
        validate_core_tables(data)
