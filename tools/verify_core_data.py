"""维护者用于检查 M0 冻结核心数据的脚本。"""

from __future__ import annotations

from pathlib import Path

from aapforge.data.core import load_core_index
from aapforge.data.tables import load_core_tables


ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    load_core_index(ROOT / "resources/core/index.json")
    load_core_tables(ROOT / "resources/core/tables.json")
    print("核心数据校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
