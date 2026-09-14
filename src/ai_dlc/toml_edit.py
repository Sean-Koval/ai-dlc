"""Comment-preserving edits of authored TOML text.

These primitives change one value or table at a time while leaving every other
byte, including comments and formatting, exactly as authored. They are not a
full TOML parser: callers validate the result with ``tomllib`` when the edit
must produce a specific configuration.
"""

from __future__ import annotations

import json
import re
import tomllib
from typing import Any

_TABLE_MARKER = "__ai_dlc_table_marker__"


def comment_suffix(value: str) -> str:
    """Return the trailing comment of one line, with the whitespace before it."""
    quote: str | None = None
    escaped = False
    for index, character in enumerate(value):
        if escaped:
            escaped = False
        elif quote == '"' and character == "\\":
            escaped = True
        elif quote is not None and character == quote:
            quote = None
        elif quote is None and character in {'"', "'"}:
            quote = character
        elif quote is None and character == "#":
            start = index
            while start and value[start - 1] in {" ", "\t"}:
                start -= 1
            return value[start:]
    return ""


def is_escaped(value: str, index: int) -> bool:
    """Whether the character at ``index`` is preceded by an odd run of backslashes."""
    backslashes = 0
    index -= 1
    while index >= 0 and value[index] == "\\":
        backslashes += 1
        index -= 1
    return bool(backslashes % 2)


def structural_lines(lines: list[str]) -> list[bool]:
    """Mark lines that begin outside a TOML multiline string."""
    multiline: str | None = None
    structural = []
    for line in lines:
        structural.append(multiline is None)
        index = 0
        single: str | None = None
        while index < len(line):
            if multiline == "basic":
                if line.startswith('"""', index) and not is_escaped(line, index):
                    multiline = None
                    index += 3
                else:
                    index += 1
            elif multiline == "literal":
                if line.startswith("'''", index):
                    multiline = None
                    index += 3
                else:
                    index += 1
            elif single == "basic":
                if line[index] == '"' and not is_escaped(line, index):
                    single = None
                index += 1
            elif single == "literal":
                if line[index] == "'":
                    single = None
                index += 1
            elif line[index] == "#":
                break
            elif line.startswith('"""', index):
                multiline = "basic"
                index += 3
            elif line.startswith("'''", index):
                multiline = "literal"
                index += 3
            elif line[index] == '"':
                single = "basic"
                index += 1
            elif line[index] == "'":
                single = "literal"
                index += 1
            else:
                index += 1
    return structural


def _marker_path(value: Any, path: tuple[str, ...] = ()) -> tuple[str, ...] | None:
    if isinstance(value, list):
        for child in value:
            found = _marker_path(child, path)
            if found is not None:
                return found
        return None
    if not isinstance(value, dict):
        return None
    if value.get(_TABLE_MARKER) is True:
        return path
    for key, child in value.items():
        found = _marker_path(child, (*path, key))
        if found is not None:
            return found
    return None


def table_path(line: str) -> tuple[str, ...] | None:
    """The dotted key path a table header line opens, or None for other lines."""
    if not line.lstrip().startswith("["):
        return None
    try:
        parsed = tomllib.loads(f"{line.rstrip()}\n{_TABLE_MARKER} = true\n")
    except tomllib.TOMLDecodeError:
        return None
    return _marker_path(parsed)


def table_paths(text: str) -> list[tuple[str, ...] | None]:
    """Per line, the table path its header opens; None for every other line."""
    lines = text.splitlines(keepends=True)
    structural = structural_lines(lines)
    return [table_path(line) if structural[index] else None for index, line in enumerate(lines)]


def set_table_value(text: str, table: str, key: str, value: str) -> str:
    """Assign one string value under ``[table]``, adding the key or table as needed.

    An existing assignment keeps its indentation, spacing and trailing comment.
    """
    lines = text.splitlines(keepends=True)
    structural = structural_lines(lines)
    paths = table_paths(text)
    target_path = tuple(table.split("."))
    start = next((index for index, path in enumerate(paths) if path == target_path), None)
    encoded = json.dumps(value, ensure_ascii=False)

    if start is None:
        if text and not text.endswith(("\n", "\r")):
            text += "\n"
        separator = "" if not text or text.endswith("\n\n") else "\n"
        return f"{text}{separator}[{table}]\n{key} = {encoded}\n"

    end = next((index for index in range(start + 1, len(lines)) if paths[index]), len(lines))
    key_pattern = rf'(?:{re.escape(key)}|"{re.escape(key)}"|\'{re.escape(key)}\')'
    assignment = re.compile(rf"^(\s*{key_pattern}\s*=\s*)(.*?)(\r?\n)?$")
    for index in range(start + 1, end):
        if not structural[index]:
            continue
        match = assignment.match(lines[index])
        if match:
            newline = match.group(3) or ""
            lines[index] = f"{match.group(1)}{encoded}{comment_suffix(match.group(2))}{newline}"
            return "".join(lines)
    prefix = ""
    if end and not lines[end - 1].endswith(("\n", "\r")):
        prefix = "\n"
    lines.insert(end, f"{prefix}{key} = {encoded}\n")
    return "".join(lines)
