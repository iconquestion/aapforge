"""源文件前端使用的结构化诊断。"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDiagnostic:
    code: str
    message: str
    file: str | None = None
    json_path: str | None = None
    line: int | None = None
    column: int | None = None
    blocking: bool = True
    suggestion: str | None = None


class SourceError(ValueError):
    def __init__(self, diagnostic: SourceDiagnostic):
        super().__init__(diagnostic.message)
        self.diagnostic = diagnostic
