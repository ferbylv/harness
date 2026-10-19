from __future__ import annotations

from typing import Any

from harness.tools.base import ToolSpec
from harness.workspace import Workspace


class WriteFile:
    spec = ToolSpec(
        name="write_file",
        description="Create or overwrite a UTF-8 text file. Parent directories are created.",
        mutating=True,
        parameters={
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
            "additionalProperties": False,
        },
    )

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, **kwargs: Any) -> str:
        path = self.workspace.resolve(str(kwargs["path"]))
        path.parent.mkdir(parents=True, exist_ok=True)
        content = str(kwargs["content"])
        path.write_text(content, encoding="utf-8")
        return f"wrote {self.workspace.rel(path)} ({len(content)} chars)"
