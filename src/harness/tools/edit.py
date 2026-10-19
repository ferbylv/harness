from __future__ import annotations

from typing import Any

from harness.tools.base import ToolSpec
from harness.workspace import Workspace


class EditFile:
    spec = ToolSpec(
        name="edit_file",
        description=(
            "Replace exactly one occurrence of old_string with new_string in a file. "
            "old_string must match uniquely; include surrounding lines if it does not."
        ),
        mutating=True,
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "old_string": {"type": "string"},
                "new_string": {"type": "string"},
            },
            "required": ["path", "old_string", "new_string"],
            "additionalProperties": False,
        },
    )

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, **kwargs: Any) -> str:
        path = self.workspace.resolve(str(kwargs["path"]))
        if not path.is_file():
            return f"file not found: {kwargs['path']}"
        old = str(kwargs["old_string"])
        new = str(kwargs["new_string"])
        if old == new:
            return "old_string and new_string are identical"
        text = path.read_text(encoding="utf-8")
        count = text.count(old)
        if count == 0:
            return "old_string not found"
        if count > 1:
            return f"old_string matched {count} times; make it unique"
        path.write_text(text.replace(old, new, 1), encoding="utf-8")
        rel = self.workspace.rel(path)
        return format_edit_hunk(rel, text, old, new)


def format_edit_hunk(rel: str, original: str, old: str, new: str) -> str:
    """Unified-ish hunk with file line numbers, for the TUI diff view."""
    idx = original.find(old)
    start = original[:idx].count("\n") + 1 if idx >= 0 else 1
    file_lines = original.splitlines()
    old_lines = old.splitlines() or [""]
    new_lines = new.splitlines() or [""]
    ctx = 3
    lines = [f"edited {rel}"]
    for n in range(max(1, start - ctx), start):
        if n <= len(file_lines):
            lines.append(f" {n}\t{file_lines[n - 1]}")
    for i, line in enumerate(old_lines):
        lines.append(f"-{start + i}\t{line}")
    for i, line in enumerate(new_lines):
        lines.append(f"+{start + i}\t{line}")
    after = start + len(old_lines)
    for n in range(after, min(len(file_lines), after + ctx - 1) + 1):
        if n >= 1:
            lines.append(f" {n}\t{file_lines[n - 1]}")
    return "\n".join(lines)
