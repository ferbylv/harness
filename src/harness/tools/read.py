from __future__ import annotations

from typing import Any

from harness.tools.base import ToolSpec
from harness.workspace import Workspace


class ReadFile:
    spec = ToolSpec(
        name="read_file",
        description="Read a UTF-8 text file. Optional 1-based start_line and line_count.",
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "start_line": {"type": "integer", "minimum": 1},
                "line_count": {"type": "integer", "minimum": 1},
            },
            "required": ["path"],
            "additionalProperties": False,
        },
    )

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, **kwargs: Any) -> str:
        path = self.workspace.resolve(str(kwargs["path"]))
        if not path.exists():
            return f"file not found: {self.workspace.rel(path)}"
        if path.is_dir():
            return f"is a directory, not a file: {self.workspace.rel(path)}"
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        start = int(kwargs.get("start_line") or 1)
        count = int(kwargs.get("line_count") or len(lines))
        start_idx = max(start - 1, 0)
        chunk = lines[start_idx : start_idx + count]
        numbered = [f"{i + start_idx + 1:>4}|{line}" for i, line in enumerate(chunk)]
        header = f"{self.workspace.rel(path)} ({len(lines)} lines)"
        return header + "\n" + "\n".join(numbered)
