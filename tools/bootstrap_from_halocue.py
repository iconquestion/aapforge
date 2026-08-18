"""维护者专用：从 HaloCue 离线索引生成核心数据候选。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from aapforge.data.bootstrap import build_core_candidate
from aapforge.data.core import validate_core_index


DEFAULT_ALLOWLIST = ROOT / "tools/bootstrap_allowlist.json"
DEFAULT_TABLES = ROOT / "resources/core/tables.json"
DEFAULT_OUTPUT = ROOT / "build/core_candidates/halocue_core_candidate.json"


def main() -> int:
    parser = argparse.ArgumentParser(description="从 HaloCue aa_resources.json 生成 Core Data 候选")
    parser.add_argument("input", help="HaloCue 离线生成的 aa_resources.json")
    parser.add_argument(
        "--allowlist",
        default=DEFAULT_ALLOWLIST,
        help="引导白名单，默认 tools/bootstrap_allowlist.json",
    )
    parser.add_argument(
        "--out",
        default=DEFAULT_OUTPUT,
        help="候选输出路径，默认 build/core_candidates/halocue_core_candidate.json",
    )
    parser.add_argument(
        "--tables",
        default=DEFAULT_TABLES,
        help="用于交叉检查的核心表，默认 resources/core/tables.json",
    )
    args = parser.parse_args()

    source = _read_json(Path(args.input))
    allowlist = _read_json(Path(args.allowlist))
    candidate = build_core_candidate(source, allowlist, tables_path=str(Path(args.tables)))
    validate_core_index(candidate)

    output = Path(args.out)
    default_core = ROOT / "resources/core/index.json"
    if output.resolve() == default_core.resolve():
        raise SystemExit("拒绝直接覆盖 resources/core/index.json；请先输出候选文件再人工审查。")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(candidate, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"已写入核心数据候选：{output}")
    return 0


def _read_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise SystemExit(f"JSON 根节点必须是对象：{path}")
    return data


if __name__ == "__main__":
    raise SystemExit(main())
