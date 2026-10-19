from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from rich.markup import escape
from rich.syntax import Syntax
from rich.text import Text

_ACTION = {
    "read_file": "Read",
    "write_file": "Write",
    "edit_file": "Edit",
    "list_dir": "List",
    "grep": "Grep",
    "bash": "Bash",
    "web_fetch": "Fetch",
}


def preview_markdown(text: str) -> str:
    """Close an unfinished fence so the live Markdown widget can render."""
    if text.count("```") % 2 == 1:
        return text + "\n```"
    return text


def parse_tool_start(payload: str) -> tuple[str, dict[str, Any]]:
    try:
        data = json.loads(payload)
        if isinstance(data, dict) and "name" in data:
            args = data.get("arguments") or {}
            return str(data["name"]), args if isinstance(args, dict) else {}
    except json.JSONDecodeError:
        pass
    name, _, rest = payload.partition(" ")
    return name, {"_raw": rest}


def format_permission(name: str, arguments: dict[str, Any]) -> str:
    """Human-readable tool call for the permission prompt. Wraps; does not dump a dict."""
    lines = [name]
    if not arguments:
        return name
    for key, value in arguments.items():
        text = str(value)
        if key in {"content", "old_string", "new_string"}:
            preview = text.splitlines()[:6]
            text = "\n".join(preview)
            if len(str(value).splitlines()) > 6:
                text += "\n…"
        lines.append(f"{key}\n{text}")
    return "\n\n".join(lines)


def action_label(name: str, arguments: dict[str, Any]) -> str:
    verb = _ACTION.get(name, name)
    detail = (
        arguments.get("path")
        or arguments.get("url")
        or arguments.get("command")
        or arguments.get("pattern")
        or ""
    )
    detail = str(detail)
    if len(detail) > 60:
        detail = detail[:57] + "…"
    return f"{verb} {detail}".strip()


def lexer_for(path: str) -> str:
    ext = Path(path).suffix.lower()
    return {
        ".py": "python",
        ".js": "javascript",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".jsx": "jsx",
        ".json": "json",
        ".md": "markdown",
        ".css": "css",
        ".html": "html",
        ".rs": "rust",
        ".go": "go",
        ".toml": "toml",
        ".yml": "yaml",
        ".yaml": "yaml",
        ".sh": "bash",
        ".zsh": "bash",
    }.get(ext, "text")


def parse_edit_hunk(result: str) -> tuple[str, list[tuple[str, int, str]]] | None:
    lines = result.splitlines()
    if not lines or not lines[0].startswith("edited "):
        return None
    path = lines[0][7:].strip()
    rows: list[tuple[str, int, str]] = []
    for line in lines[1:]:
        if not line:
            continue
        op = line[0]
        rest = line[1:]
        num, sep, body = rest.partition("\t")
        if not sep:
            body = rest
            num = "0"
        try:
            n = int(num)
        except ValueError:
            n = 0
        rows.append((op, n, body))
    if not rows:
        return None
    return path, rows


def highlight_code(code: str, lexer: str) -> Text:
    if not code:
        return Text("")
    try:
        syntax = Syntax(code, lexer, theme="monokai", word_wrap=False)
        text = syntax.highlight(code)
    except Exception:
        return Text(code)
    text.rstrip()
    return text


def render_diff_line(op: str, number: int, body: str, lexer: str) -> Text:
    code = highlight_code(body, lexer)
    num = f"{number:>4}  "
    if op == "-":
        row = Text(num, style="bold #e06c75")
        code.stylize("not dim")
        row.append_text(code)
        return row
    if op == "+":
        row = Text(num, style="bold #98c379")
        code.stylize("not dim")
        row.append_text(code)
        return row
    row = Text(num, style="#5c6370")
    row.append_text(code)
    return row


def render_diff_markup(result: str) -> str | None:
    parsed = parse_edit_hunk(result)
    if parsed is None:
        return None
    path, rows = parsed
    lexer = lexer_for(path)
    return "\n".join(render_diff_line(op, n, body, lexer).plain for op, n, body in rows)
