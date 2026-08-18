"""规范中间表示。

规范中间表示会消除默认值和兼容简写；后续阶段不需要再理解这些输入变体。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class CanonicalSource:
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return self.data
