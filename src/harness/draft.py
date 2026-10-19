from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from uuid import uuid4

from harness.clipboard import sniff_mime

LARGE_PASTE = 1000
MAX_IMAGE_BYTES = 8 * 1024 * 1024

_CHIP = re.compile(r"\[Image #(\d+)\]")
_PASTE = re.compile(r"\[Pasted Content (\d+) chars · ([a-z0-9]+)\]")


@dataclass
class ImageChip:
    index: int
    mime: str
    data: bytes


@dataclass
class Draft:
    images: dict[int, ImageChip] = field(default_factory=dict)
    pastes: dict[str, str] = field(default_factory=dict)
    _next_image: int = 1

    def add_image(self, data: bytes, mime: str | None = None) -> str | None:
        mime = mime or sniff_mime(data)
        if not mime or len(data) > MAX_IMAGE_BYTES or not data:
            return None
        index = self._next_image
        self._next_image += 1
        self.images[index] = ImageChip(index=index, mime=mime, data=data)
        return f"[Image #{index}]"

    def add_paste(self, text: str) -> str:
        paste_id = uuid4().hex[:6]
        self.pastes[paste_id] = text
        return f"[Pasted Content {len(text)} chars · {paste_id}]"

    def expand(self, buffer: str) -> str | list[dict]:
        text = _PASTE.sub(lambda m: self.pastes.get(m.group(2), m.group(0)), buffer)
        chips = list(_CHIP.finditer(text))
        if not chips:
            return text
        parts: list[dict] = []
        cursor = 0
        for match in chips:
            if match.start() > cursor:
                chunk = text[cursor : match.start()]
                if chunk:
                    parts.append({"type": "text", "text": chunk})
            chip = self.images.get(int(match.group(1)))
            if chip:
                encoded = base64.b64encode(chip.data).decode("ascii")
                parts.append(
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:{chip.mime};base64,{encoded}"},
                    }
                )
            cursor = match.end()
        if cursor < len(text):
            tail = text[cursor:]
            if tail:
                parts.append({"type": "text", "text": tail})
        return parts or text
