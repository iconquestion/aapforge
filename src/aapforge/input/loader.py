"""读取 `.aapforge.json` 和 `.aapforge.jsonc` 源文件。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from aapforge.input.diagnostics import SourceDiagnostic, SourceError
from aapforge.input.jsonc import strip_jsonc
from aapforge.input.normalizer import normalize_source
from aapforge.input.schema_validator import validate_source_schema
from aapforge.ir.canonical import CanonicalSource


def load_source(path: str | Path) -> CanonicalSource:
    source_path = Path(path)
    text = source_path.read_text(encoding="utf-8")
    return load_source_text(text, file=str(source_path), jsonc=source_path.suffix.lower() == ".jsonc")


def load_source_text(text: str, *, file: str | None = None, jsonc: bool = False) -> CanonicalSource:
    parsed = parse_source_text(text, file=file, jsonc=jsonc)
    validate_source_schema(parsed, file=file)
    return normalize_source(parsed, file=file)


def parse_source_text(text: str, *, file: str | None = None, jsonc: bool = False) -> Any:
    payload = strip_jsonc(text) if jsonc else text
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SourceError(
            SourceDiagnostic(
                code="E_JSON_PARSE",
                message=exc.msg,
                file=file,
                line=exc.lineno,
                column=exc.colno,
            )
        ) from exc
