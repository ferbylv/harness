from __future__ import annotations

from harness.cancel import CancelToken
from harness.types import DeltaFn, LLMResponse, Message, Role, ToolCall, Usage


class MockClient:
    """Deterministic stand-in so the loop can run without an API key."""

    def __init__(self, cancel: CancelToken | None = None) -> None:
        self._turns = 0
        self.cancel = cancel

    def complete(
        self,
        messages: list[Message],
        tools: list[dict],
        on_delta: DeltaFn | None = None,
        on_thinking: DeltaFn | None = None,
    ) -> LLMResponse:
        del tools
        if self.cancel:
            self.cancel.throw_if_set()
        self._turns += 1
        last_user = next((m.content for m in reversed(messages) if m.role is Role.USER), "")
        prompt_tokens = max(sum(len(m.content) for m in messages) // 4, 1)
        if self._turns == 1:
            return LLMResponse(
                text="",
                tool_calls=[
                    ToolCall(
                        id="mock_list",
                        name="list_dir",
                        arguments={"path": "."},
                    )
                ],
                usage=Usage(prompt_tokens=prompt_tokens, completion_tokens=8),
            )
        text = (
            f"(mock) saw your request: {last_user!r}\n"
            "listed the workspace and stopped. set HARNESS_MOCK=0 to talk to a real model."
        )
        if on_delta:
            for i in range(0, len(text), 24):
                on_delta(text[i : i + 24])
        return LLMResponse(
            text=text,
            usage=Usage(prompt_tokens=prompt_tokens, completion_tokens=max(len(text) // 4, 1)),
        )
