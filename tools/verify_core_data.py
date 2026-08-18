"""维护者用于检查核心数据的脚本。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aapforge.data.core import load_core_index
from aapforge.data.tables import load_core_tables


def main() -> int:
    parser = argparse.ArgumentParser(description="检查 AAPForge 核心数据")
    parser.add_argument(
        "index",
        nargs="?",
        default=ROOT / "resources/core/index.json",
        help="要检查的核心索引，默认 resources/core/index.json",
    )
    args = parser.parse_args()
    load_core_index(Path(args.index))
    load_core_tables(ROOT / "resources/core/tables.json")
    print("核心数据校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
