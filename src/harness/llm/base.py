from __future__ import annotations

from typing import Protocol

from harness.types import DeltaFn, LLMResponse, Message


class LLMClient(Protocol):
    def complete(
        self,
        messages: list[Message],
        tools: list[dict],
        on_delta: DeltaFn | None = None,
        on_thinking: DeltaFn | None = None,
    ) -> LLMResponse:
        """One chat turn. on_delta is visible text; on_thinking is reasoning."""
