from __future__ import annotations

import subprocess
from typing import Any

from harness.cancel import CancelToken, Cancelled
from harness.tools.base import ToolSpec
from harness.workspace import Workspace


class Bash:
    spec = ToolSpec(
        name="bash",
        description="Run a shell command in the workspace. Returns stdout, stderr, and exit code.",
        mutating=True,
        parameters={
            "type": "object",
            "properties": {
                "command": {"type": "string"},
                "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 120},
            },
            "required": ["command"],
            "additionalProperties": False,
        },
    )

    def __init__(self, workspace: Workspace, cancel: CancelToken | None = None) -> None:
        self.workspace = workspace
        self.cancel = cancel

    def run(self, **kwargs: Any) -> str:
        command = str(kwargs["command"])
        timeout = int(kwargs.get("timeout_seconds") or 30)
        if self.cancel:
            self.cancel.throw_if_set()
        try:
            proc = subprocess.Popen(
                command,
                shell=True,
                cwd=self.workspace.root,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                start_new_session=True,
            )
        except OSError as exc:
            return f"tool error (OSError): {exc}"
        if self.cancel:
            self.cancel.set_process(proc)
        try:
            stdout, stderr = proc.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            proc.kill()
            return f"timed out after {timeout}s"
        if self.cancel and self.cancel.is_set():
            raise Cancelled()
        parts = [
            f"exit {proc.returncode}",
            _block("stdout", stdout),
            _block("stderr", stderr),
        ]
        return "\n".join(part for part in parts if part)


def _block(label: str, text: str) -> str:
    text = (text or "").rstrip()
    if not text:
        return ""
    return f"{label}:\n{text}"
