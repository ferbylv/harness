from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from harness.types import Message, Role, ToolCall, Usage
from harness.workspace import Workspace


def _now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


@dataclass
class Session:
    id: str
    messages: list[Message]
    model: str = ""
    created_at: str = ""
    updated_at: str = ""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cost_usd: float = 0.0
    last_prompt_tokens: int = 0

    @classmethod
    def start(cls, workspace: Workspace, model: str = "") -> Session:
        del workspace
        now = _now()
        return cls(id=uuid4().hex[:12], messages=[], model=model, created_at=now, updated_at=now)

    def add(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = _now()

    def reset(self, workspace: Workspace, model: str = "") -> None:
        fresh = Session.start(workspace, model=model or self.model)
        self.id = fresh.id
        self.messages = []
        self.created_at = fresh.created_at
        self.updated_at = fresh.updated_at
        self.prompt_tokens = 0
        self.completion_tokens = 0
        self.cost_usd = 0.0
        self.last_prompt_tokens = 0
        if model:
            self.model = model

    def record_usage(self, usage: Usage) -> None:
        self.prompt_tokens += usage.prompt_tokens
        self.completion_tokens += usage.completion_tokens
        self.cost_usd += usage.cost_usd
        if usage.prompt_tokens:
            self.last_prompt_tokens = usage.prompt_tokens
        self.updated_at = _now()

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "model": self.model,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "cost_usd": self.cost_usd,
            "last_prompt_tokens": self.last_prompt_tokens,
            "messages": [_dump_message(m) for m in self.messages],
        }

    @classmethod
    def load(cls, path: Path) -> Session:
        data = json.loads(path.read_text(encoding="utf-8"))
        messages = [_load_message(m) for m in data.get("messages") or []]
        # Older files stored the system prompt as messages[0]. Drop it; we rebuild.
        if messages and messages[0].role is Role.SYSTEM:
            messages = messages[1:]
        return cls(
            id=data.get("id") or uuid4().hex[:12],
            messages=messages,
            model=str(data.get("model") or ""),
            created_at=str(data.get("created_at") or ""),
            updated_at=str(data.get("updated_at") or ""),
            prompt_tokens=int(data.get("prompt_tokens") or 0),
            completion_tokens=int(data.get("completion_tokens") or 0),
            cost_usd=float(data.get("cost_usd") or 0),
            last_prompt_tokens=int(data.get("last_prompt_tokens") or 0),
        )


def _dump_message(message: Message) -> dict:
    return {
        "role": message.role.value,
        "content": message.content,
        "tool_calls": [asdict(c) for c in message.tool_calls],
        "tool_call_id": message.tool_call_id,
        "name": message.name,
    }


def _load_message(raw: dict) -> Message:
    return Message(
        role=Role(raw["role"]),
        content=raw["content"] if "content" in raw and raw["content"] is not None else "",
        tool_calls=[ToolCall(**c) for c in raw.get("tool_calls") or []],
        tool_call_id=raw.get("tool_call_id"),
        name=raw.get("name"),
    )
