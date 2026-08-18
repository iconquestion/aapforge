"""JSONC 读取辅助：保留行列位置，去掉注释和尾逗号。"""

from __future__ import annotations


def strip_jsonc(text: str) -> str:
    out: list[str] = []
    index = 0
    in_string = False
    escape = False
    while index < len(text):
        char = text[index]
        nxt = text[index + 1] if index + 1 < len(text) else ""
        if in_string:
            out.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue
        if char == "/" and nxt == "/":
            out.extend("  ")
            index += 2
            while index < len(text) and text[index] not in "\r\n":
                out.append(" ")
                index += 1
            continue
        if char == "/" and nxt == "*":
            out.extend("  ")
            index += 2
            while index < len(text):
                if text[index] == "*" and index + 1 < len(text) and text[index + 1] == "/":
                    out.extend("  ")
                    index += 2
                    break
                out.append("\n" if text[index] == "\n" else " ")
                index += 1
            continue
        if char == ",":
            probe = index + 1
            while probe < len(text) and text[probe].isspace():
                probe += 1
            if probe < len(text) and text[probe] in "]}":
                out.append(" ")
                index += 1
                continue
        out.append(char)
        index += 1
    return _strip_trailing_commas("".join(out))


def _strip_trailing_commas(text: str) -> str:
    out: list[str] = []
    index = 0
    in_string = False
    escape = False
    while index < len(text):
        char = text[index]
        if in_string:
            out.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == '"':
                in_string = False
            index += 1
            continue
        if char == '"':
            in_string = True
            out.append(char)
            index += 1
            continue
        if char == ",":
            probe = index + 1
            while probe < len(text) and text[probe].isspace():
                probe += 1
            if probe < len(text) and text[probe] in "]}":
                out.append(" ")
                index += 1
                continue
        out.append(char)
        index += 1
    return "".join(out)
