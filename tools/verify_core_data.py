"""Maintainer check for frozen M0 core data."""

from __future__ import annotations

from pathlib import Path

from aapforge.data.core import load_core_index
from aapforge.data.tables import load_core_tables


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    load_core_index(ROOT / "resources/core/index.json")
    load_core_tables(ROOT / "resources/core/tables.json")
    print("core data ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
