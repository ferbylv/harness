from __future__ import annotations

from typing import Protocol, runtime_checkable

from harness.runtime import Runtime

# Loop → UI. A front-end must handle these kinds; unknown kinds should be ignored.
EVENT_KINDS = (
    "thinking_delta",
    "text_delta",
    "assistant_end",
    "tool_start",
    "tool_end",
    "status",
)

# PermissionGate.ask return values a front-end may produce.
ASK_ONCE = "once"
ASK_ALWAYS_TOOL = "always_tool"
ASK_ALWAYS = "always"
ASK_DENY = "deny"


@runtime_checkable
class UserInterface(Protocol):
    """Swap-in front-end.

    Contract:
    - Do not call the LLM or tools yourself. Use Runtime.submit / handle_command.
    - Stream by setting runtime.loop.on_event to a callable (kind, payload).
    - Permissions by setting runtime.loop.permissions.ask to a callable(ToolCall).
    - Ignore unknown event kinds so the loop can grow without breaking you.
    """

    name: str

    def run(self, runtime: Runtime) -> int:
        """Block until the user quits. Return a process exit code."""
        ...
