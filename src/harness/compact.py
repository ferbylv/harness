from __future__ import annotations

from harness.content import text_of
from harness.types import Message, Role, Usage


def should_compact(
    messages: list[Message],
    *,
    last_prompt_tokens: int,
    compact_at: int,
) -> bool:
    if compact_at <= 0:
        return False
    if last_prompt_tokens >= compact_at:
        return True
    if last_prompt_tokens > 0:
        return False
    # No usage from the provider: rough char heuristic (~4 chars/token).
    chars = sum(len(text_of(m.content)) for m in messages)
    return (chars // 4) >= compact_at


def split_for_compact(messages: list[Message], *, keep_last: int) -> tuple[list[Message], list[Message]]:
    """Drop a prefix; snap the keep window to a user turn so tool pairs stay intact."""
    transcript = [m for m in messages if m.role is not Role.SYSTEM]
    if len(transcript) <= keep_last:
        return [], transcript
    start = len(transcript) - keep_last
    while start > 0 and transcript[start].role is not Role.USER:
        start -= 1
    if start <= 0:
        return [], transcript
    return transcript[:start], transcript[start:]


def stub_summary(dropped: list[Message]) -> str:
    files: list[str] = []
    for message in dropped:
        if message.role is Role.ASSISTANT:
            for call in message.tool_calls:
                path = str((call.arguments or {}).get("path") or "")
                if path:
                    files.append(path)
    unique = ", ".join(dict.fromkeys(files)) if files else "none recorded"
    return (
        f"[compacted {len(dropped)} earlier messages. "
        f"files mentioned in tool calls: {unique}. "
        "continue from recent context.]"
    )


def apply_compact(messages: list[Message], *, keep_last: int, summary: str | None = None) -> list[Message] | None:
    prefix, tail = split_for_compact(messages, keep_last=keep_last)
    if not prefix:
        return None
    stub = Message(role=Role.USER, content=summary or stub_summary(prefix))
    return [stub, *tail]


def usage_over_budget(usage: Usage, compact_at: int) -> bool:
    return compact_at > 0 and usage.prompt_tokens >= compact_at
