from __future__ import annotations

from typing import Any

Content = str | list[Any]


def text_of(content: Content) -> str:
    if isinstance(content, str):
        return content
    parts: list[str] = []
    for block in content:
        if not isinstance(block, dict):
            continue
        if block.get("type") == "text":
            parts.append(str(block.get("text") or ""))
        elif block.get("type") == "image_url":
            parts.append("[image]")
    return "".join(parts)


def has_images(content: Content) -> bool:
    if isinstance(content, str):
        return False
    return any(isinstance(b, dict) and b.get("type") == "image_url" for b in content)
