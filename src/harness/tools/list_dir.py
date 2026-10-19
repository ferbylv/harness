from __future__ import annotations

from typing import Any

from harness.tools.base import ToolSpec
from harness.workspace import Workspace


class ListDir:
    spec = ToolSpec(
        name="list_dir",
        description="List files and directories in a folder (non-recursive).",
        parameters={
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": [],
            "additionalProperties": False,
        },
    )

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, **kwargs: Any) -> str:
        path = self.workspace.resolve(str(kwargs.get("path") or "."))
        if not path.exists():
            return f"not found: {kwargs.get('path')}"
        if path.is_file():
            return f"is a file: {self.workspace.rel(path)}"
        entries = sorted(path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        if not entries:
            return "(empty)"
        lines = []
        for entry in entries:
            suffix = "/" if entry.is_dir() else ""
            lines.append(f"{entry.name}{suffix}")
        return "\n".join(lines)
