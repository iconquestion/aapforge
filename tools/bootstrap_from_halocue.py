"""维护者专用的 HaloCue 引导说明。

M0 数据来自明确的 HaloCue 模块，经人工审查后写入 AAPForge 自有 JSON。
这个占位工具刻意不导入 HaloCue 运行时代码，也不扫描本机 AA 安装或用户资源目录。
"""

from __future__ import annotations


def main() -> int:
    print("M0 未定义自动引导流程；请查看 docs/aap_契约.md。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
