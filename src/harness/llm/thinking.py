from __future__ import annotations

from typing import Any

_OPEN = "<think>"
_CLOSE = "</think>"


def extract_thinking(obj: dict[str, Any] | None) -> str:
    """Pull reasoning text out of OpenAI-compat delta/message payloads."""
    if not isinstance(obj, dict):
        return ""
    for key in ("reasoning_content", "reasoning", "thinking"):
        value = obj.get(key)
        if isinstance(value, str) and value:
            return value
        if isinstance(value, dict):
            inner = value.get("content") or value.get("text") or value.get("summary")
            if isinstance(inner, str) and inner:
                return inner
    return ""


class ThinkSplitter:
    """Split streamed content that inlines <think>...</think> (Qwen and friends)."""

    def __init__(self) -> None:
        self.in_think = False
        self.buf = ""

    def feed(self, piece: str) -> list[tuple[str, str]]:
        if not piece:
            return []
        self.buf += piece
        events: list[tuple[str, str]] = []
        while self.buf:
            if self.in_think:
                end = self.buf.find(_CLOSE)
                if end == -1:
                    keep = _ambiguous_suffix(self.buf, _CLOSE)
                    emit, self.buf = self.buf[: len(self.buf) - keep], self.buf[len(self.buf) - keep :]
                    if emit:
                        events.append(("thinking", emit))
                    break
                if end:
                    events.append(("thinking", self.buf[:end]))
                self.buf = self.buf[end + len(_CLOSE) :]
                self.in_think = False
                continue
            start = self.buf.find(_OPEN)
            if start == -1:
                keep = _ambiguous_suffix(self.buf, _OPEN)
                emit, self.buf = self.buf[: len(self.buf) - keep], self.buf[len(self.buf) - keep :]
                if emit:
                    events.append(("text", emit))
                break
            if start:
                events.append(("text", self.buf[:start]))
            self.buf = self.buf[start + len(_OPEN) :]
            self.in_think = True
        return events

    def flush(self) -> list[tuple[str, str]]:
        if not self.buf:
            return []
        kind = "thinking" if self.in_think else "text"
        leftover = self.buf
        self.buf = ""
        return [(kind, leftover)]


def _ambiguous_suffix(text: str, tag: str) -> int:
    max_keep = min(len(text), len(tag) - 1)
    for n in range(max_keep, 0, -1):
        if tag.startswith(text[-n:]):
            return n
    return 0
