from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Any

from harness.tools.base import ToolSpec
from harness.workspace import Workspace

_SKIP_DIRS = {".git", ".venv", "__pycache__", "node_modules", ".harness", "dist"}


class Grep:
    spec = ToolSpec(
        name="grep",
        description="Search file contents with a Python regex. Case-insensitive optional.",
        parameters={
            "type": "object",
            "properties": {
                "pattern": {"type": "string"},
                "path": {"type": "string", "description": "File or directory. Default: workspace root."},
                "glob": {"type": "string", "description": "Filename glob, e.g. *.py"},
                "max_matches": {"type": "integer", "minimum": 1, "maximum": 200},
            },
            "required": ["pattern"],
            "additionalProperties": False,
        },
    )

    def __init__(self, workspace: Workspace) -> None:
        self.workspace = workspace

    def run(self, **kwargs: Any) -> str:
        try:
            regex = re.compile(str(kwargs["pattern"]))
        except re.error as exc:
            return f"invalid regex: {exc}"
        root = self.workspace.resolve(str(kwargs.get("path") or "."))
        glob = str(kwargs.get("glob") or "*")
        limit = int(kwargs.get("max_matches") or 50)
        hits: list[str] = []
        files = [root] if root.is_file() else _iter_files(root, glob)
        for file in files:
            try:
                lines = file.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            for i, line in enumerate(lines, start=1):
                if regex.search(line):
                    rel = self.workspace.rel(file)
                    hits.append(f"{rel}:{i}:{line}")
                    if len(hits) >= limit:
                        return "\n".join(hits) + "\n(hit match cap)"
        return "\n".join(hits) if hits else "no matches"


def _iter_files(root: Path, glob: str):
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in _SKIP_DIRS]
        for name in filenames:
            path = Path(dirpath) / name
            if glob != "*" and not fnmatch.fnmatch(name, glob):
                continue
            yield path
