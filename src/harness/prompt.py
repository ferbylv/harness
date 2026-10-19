from __future__ import annotations

from harness.context import build_system_prompt
from harness.workspace import Workspace


def load_system_prompt(workspace: Workspace) -> str:
    return build_system_prompt(workspace)
