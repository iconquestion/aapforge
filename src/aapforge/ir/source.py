"""源文件原始结构类型。

M1 阶段不为原始输入建立复杂模型；读取结果先保留为 Python 字典，再进入结构校验。
"""

from __future__ import annotations

from typing import Any

RawSource = dict[str, Any]
