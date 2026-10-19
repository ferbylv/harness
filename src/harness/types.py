from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from harness.content import Content

DeltaFn = Callable[[str], None]


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def add(self, other: Usage) -> None:
        self.prompt_tokens += other.prompt_tokens
        self.completion_tokens += other.completion_tokens
        self.cost_usd += other.cost_usd


@dataclass
class Message:
    role: Role
    content: Content = ""
    tool_calls: list[ToolCall] = field(default_factory=list)
    tool_call_id: str | None = None
    name: str | None = None

    def to_openai(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"role": self.role.value}
        if self.role is Role.TOOL:
            payload["tool_call_id"] = self.tool_call_id
            payload["content"] = self.content
            if self.name:
                payload["name"] = self.name
            return payload
        if self.role is Role.ASSISTANT and self.tool_calls:
            payload["content"] = self.content or None
            payload["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": _dump_args(call.arguments),
                    },
                }
                for call in self.tool_calls
            ]
            return payload
        payload["content"] = self.content
        return payload


@dataclass
class LLMResponse:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    raw: dict[str, Any] = field(default_factory=dict)
    usage: Usage = field(default_factory=Usage)
    thinking: str = ""

    @property
    def done(self) -> bool:
        return not self.tool_calls


def parse_usage(data: dict[str, Any] | None) -> Usage:
    raw = (data or {}).get("usage") if isinstance(data, dict) else None
    if not isinstance(raw, dict):
        return Usage()
    prompt = _int(raw.get("prompt_tokens") or raw.get("input_tokens"))
    completion = _int(raw.get("completion_tokens") or raw.get("output_tokens"))
    cost = raw.get("cost")
    if cost is None:
        cost = raw.get("total_cost")
    try:
        cost_usd = float(cost or 0)
    except (TypeError, ValueError):
        cost_usd = 0.0
    return Usage(prompt_tokens=prompt, completion_tokens=completion, cost_usd=cost_usd)


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _dump_args(arguments: dict[str, Any]) -> str:
    import json

    return json.dumps(arguments, ensure_ascii=False)
