from __future__ import annotations

from harness.tools.base import Tool
from harness.types import ToolCall


class ToolRegistry:
    def __init__(self, tools: list[Tool], max_output: int = 80_000) -> None:
        self._tools = {tool.spec.name: tool for tool in tools}
        self.max_output = max_output

    def schemas(self) -> list[dict]:
        return [tool.spec.schema() for tool in self._tools.values()]

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def dispatch(self, call: ToolCall) -> str:
        tool = self._tools.get(call.name)
        if tool is None:
            known = ", ".join(sorted(self._tools)) or "(none)"
            return f"unknown tool {call.name!r}. known: {known}"
        output = tool.run(**call.arguments)
        return _clip(output, self.max_output)


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    omitted = len(text) - limit
    return text[:limit] + f"\n...[truncated {omitted} chars]"
