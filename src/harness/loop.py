from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field

from harness.cancel import CancelToken, Cancelled
from harness.compact import apply_compact, should_compact, stub_summary, split_for_compact
from harness.content import Content, text_of
from harness.llm.base import LLMClient
from harness.permissions import PermissionGate
from harness.session import Session
from harness.skills import Skill
from harness.tools.registry import ToolRegistry
from harness.types import LLMResponse, Message, Role, ToolCall, Usage

EventHandler = Callable[[str, str], None]
SystemBuilder = Callable[[str, list[Skill]], str]


@dataclass
class LoopResult:
    text: str
    turns: int
    stopped_reason: str
    usage: Usage = field(default_factory=Usage)
    compacted: bool = False


class AgentLoop:
    """The whole harness in one function: model -> tools -> model, until it stops."""

    def __init__(
        self,
        *,
        llm: LLMClient,
        tools: ToolRegistry,
        session: Session,
        permissions: PermissionGate,
        max_turns: int = 30,
        on_event: EventHandler | None = None,
        build_system: SystemBuilder | None = None,
        compact_at: int = 32_000,
        keep_last: int = 16,
        compact_summarize: bool = False,
        cancel: CancelToken | None = None,
    ) -> None:
        self.llm = llm
        self.tools = tools
        self.session = session
        self.permissions = permissions
        self.max_turns = max_turns
        self.on_event = on_event or (lambda _kind, _payload: None)
        self.build_system = build_system or (lambda _user, _skills: "You are a coding agent.")
        self.compact_at = compact_at
        self.keep_last = keep_last
        self.compact_summarize = compact_summarize
        self.cancel = cancel or CancelToken()

    def run(
        self,
        user_text: str,
        *,
        injected: list[Skill] | None = None,
        content: Content | None = None,
    ) -> LoopResult:
        injected = injected or []
        system = self.build_system(user_text, injected)
        self.session.add(Message(role=Role.USER, content=user_text if content is None else content))
        last_text = ""
        run_usage = Usage()
        compacted = False
        try:
            for turn in range(1, self.max_turns + 1):
                self.cancel.throw_if_set()
                if self._maybe_compact():
                    compacted = True
                streamed = False

                def _on_delta(chunk: str) -> None:
                    nonlocal streamed
                    streamed = True
                    self.on_event("text_delta", chunk)

                def _on_thinking(chunk: str) -> None:
                    nonlocal streamed
                    streamed = True
                    self.on_event("thinking_delta", chunk)

                outgoing = [Message(role=Role.SYSTEM, content=system), *self.session.messages]
                response = self.llm.complete(
                    outgoing, self.tools.schemas(), _on_delta, on_thinking=_on_thinking
                )
                self.session.add(_assistant_message(response))
                self.session.record_usage(response.usage)
                run_usage.add(response.usage)
                if response.thinking and not streamed:
                    self.on_event("thinking_delta", response.thinking)
                if response.text:
                    if not streamed:
                        self.on_event("text_delta", response.text)
                    last_text = response.text
                if response.text or response.thinking or streamed:
                    self.on_event("assistant_end", "")
                if response.done:
                    return LoopResult(
                        text=last_text,
                        turns=turn,
                        stopped_reason="model",
                        usage=run_usage,
                        compacted=compacted,
                    )
                for call in response.tool_calls:
                    self.cancel.throw_if_set()
                    result = self._run_tool(call)
                    self.session.add(
                        Message(
                            role=Role.TOOL,
                            content=result,
                            tool_call_id=call.id,
                            name=call.name,
                        )
                    )
            return LoopResult(
                text=last_text or "(hit max_turns without a final answer)",
                turns=self.max_turns,
                stopped_reason="max_turns",
                usage=run_usage,
                compacted=compacted,
            )
        except (Cancelled, KeyboardInterrupt):
            self._seal_open_tools("cancelled by user")
            self.on_event("assistant_end", "")
            self.on_event("status", "cancelled")
            return LoopResult(
                text=last_text or "(cancelled)",
                turns=0,
                stopped_reason="cancelled",
                usage=run_usage,
                compacted=compacted,
            )

    def compact_now(self) -> bool:
        return self._maybe_compact(force=True)

    def _maybe_compact(self, *, force: bool = False) -> bool:
        if not force and not should_compact(
            self.session.messages,
            last_prompt_tokens=self.session.last_prompt_tokens,
            compact_at=self.compact_at,
        ):
            return False
        prefix, _tail = split_for_compact(self.session.messages, keep_last=self.keep_last)
        if not prefix:
            return False
        self.on_event("status", "compacting context")
        summary = self._summarize(prefix) if self.compact_summarize else stub_summary(prefix)
        compacted = apply_compact(self.session.messages, keep_last=self.keep_last, summary=summary)
        if compacted is None:
            return False
        self.session.messages = compacted
        self.session.last_prompt_tokens = 0
        return True

    def _summarize(self, dropped: list[Message]) -> str:
        fallback = stub_summary(dropped)
        transcript = _transcript(dropped)
        prompt = (
            "Summarize this coding-agent transcript for future turns. "
            "Keep files touched, decisions, errors, and remaining work. "
            "Drop chatter. Plain text, under 800 words.\n\n"
            + transcript[:80_000]
        )
        try:
            response = self.llm.complete(
                [
                    Message(role=Role.SYSTEM, content="You compress conversation history."),
                    Message(role=Role.USER, content=prompt),
                ],
                [],
            )
        except Exception:
            return fallback
        text = (response.text or "").strip()
        return text or fallback

    def _run_tool(self, call: ToolCall) -> str:
        self.on_event(
            "tool_start",
            json.dumps({"name": call.name, "arguments": call.arguments}, ensure_ascii=False, default=str),
        )
        allowed, reason = self.permissions.allow(call)
        if not allowed:
            text = f"permission denied: {reason}"
            self.on_event("tool_end", text)
            return text
        try:
            text = self.tools.dispatch(call)
        except Cancelled:
            raise
        except Exception as exc:  # tool bugs must not kill the loop
            text = f"tool error ({type(exc).__name__}): {exc}"
        self.on_event("tool_end", text)
        return text

    def _seal_open_tools(self, text: str) -> None:
        if not self.session.messages:
            return
        last = self.session.messages[-1]
        if last.role is not Role.ASSISTANT or not last.tool_calls:
            return
        have = {m.tool_call_id for m in self.session.messages if m.role is Role.TOOL}
        for call in last.tool_calls:
            if call.id in have:
                continue
            self.session.add(
                Message(role=Role.TOOL, content=text, tool_call_id=call.id, name=call.name)
            )


def _assistant_message(response: LLMResponse) -> Message:
    return Message(
        role=Role.ASSISTANT,
        content=response.text,
        tool_calls=list(response.tool_calls),
    )


def _transcript(messages: list[Message]) -> str:
    lines: list[str] = []
    for message in messages:
        if message.role is Role.ASSISTANT and message.tool_calls:
            names = ", ".join(c.name for c in message.tool_calls)
            lines.append(f"assistant: (tools: {names}) {text_of(message.content)}".rstrip())
        else:
            lines.append(f"{message.role.value}: {text_of(message.content)}")
    return "\n".join(lines)
