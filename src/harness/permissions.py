from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from harness.tools.registry import ToolRegistry
from harness.types import ToolCall

# True/False kept for tests. Strings: once | always_tool | always | deny
AskFn = Callable[[ToolCall], bool | str]


@dataclass
class PermissionGate:
    """Mutating tools ask. Session can remember a tool, or YOLO everything."""

    tools: ToolRegistry
    yolo: bool = False
    ask: AskFn | None = None
    session_tools: set[str] = field(default_factory=set)

    def allow(self, call: ToolCall) -> tuple[bool, str]:
        tool = self.tools.get(call.name)
        if tool is None:
            return True, "unknown tool handled by registry"
        if not tool.spec.mutating:
            return True, "read-only"
        if self.yolo:
            return True, "yolo"
        if call.name in self.session_tools:
            return True, "session tool"
        if self.ask is None:
            return True, "no ask hook"
        decision = self.ask(call)
        if decision is True or decision == "once":
            return True, "user allowed"
        if decision == "always_tool":
            self.session_tools.add(call.name)
            return True, "always this tool"
        if decision == "always":
            self.yolo = True
            return True, "yolo"
        return False, "user denied"
