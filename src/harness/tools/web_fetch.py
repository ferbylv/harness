from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

import httpx

from harness.tools.base import ToolSpec

_ALLOWED = {"http", "https"}
_MAX_BYTES = 200_000
_UA = "harness/0.1 web_fetch"


class WebFetch:
    spec = ToolSpec(
        name="web_fetch",
        description=(
            "Fetch a public http(s) URL and return text. Use for docs, APIs, weather pages "
            "(e.g. https://wttr.in/Beijing?format=3). Not a search engine: you must already have a URL."
        ),
        parameters={
            "type": "object",
            "properties": {
                "url": {"type": "string"},
                "timeout_seconds": {"type": "integer", "minimum": 1, "maximum": 60},
            },
            "required": ["url"],
            "additionalProperties": False,
        },
    )

    def __init__(self, client: httpx.Client | None = None, max_bytes: int = _MAX_BYTES) -> None:
        self._client = client
        self.max_bytes = max_bytes

    def run(self, **kwargs: Any) -> str:
        url = str(kwargs.get("url") or "").strip()
        blocked = _reject_url(url)
        if blocked:
            return blocked
        timeout = int(kwargs.get("timeout_seconds") or 20)
        try:
            if self._client is not None:
                response = self._client.get(url, timeout=timeout)
            else:
                with httpx.Client(
                    follow_redirects=True,
                    timeout=timeout,
                    headers={"User-Agent": _UA, "Accept": "*/*"},
                ) as client:
                    response = client.get(url)
        except httpx.TimeoutException:
            return f"timed out fetching {url}"
        except httpx.RequestError as exc:
            return f"request failed: {exc}"
        final = str(response.url)
        blocked = _reject_url(final)
        if blocked:
            return f"blocked redirect to {final}"
        body = response.content[: self.max_bytes]
        truncated = len(response.content) > self.max_bytes
        content_type = (response.headers.get("content-type") or "").split(";")[0].strip().lower()
        text = _decode_body(content_type, body)
        header = f"HTTP {response.status_code} {final} ({content_type or 'unknown'}, {len(body)} bytes)"
        if truncated:
            header += f" truncated to {self.max_bytes} bytes"
        return header + "\n" + text


def _reject_url(url: str) -> str | None:
    if not url:
        return "url is required"
    parsed = urlparse(url)
    if parsed.scheme.lower() not in _ALLOWED:
        return f"only http/https allowed, got {parsed.scheme or 'no scheme'}"
    if not parsed.netloc:
        return "url host is missing"
    return None


def _decode_body(content_type: str, body: bytes) -> str:
    if content_type.startswith("image/") or content_type in {"application/octet-stream", "application/pdf"}:
        return f"binary {content_type}; not shown"
    text = body.decode("utf-8", errors="replace")
    if "json" in content_type:
        try:
            return json.dumps(json.loads(text), ensure_ascii=False, indent=2)
        except json.JSONDecodeError:
            return text
    if "html" in content_type:
        return _html_to_text(text)
    return text


def _html_to_text(html: str) -> str:
    html = re.sub(r"(?is)<(script|style)[^>]*>.*?</\1>", " ", html)
    html = re.sub(r"(?is)<br\s*/?>", "\n", html)
    html = re.sub(r"(?is)</p>", "\n\n", html)
    html = re.sub(r"(?is)<[^>]+>", " ", html)
    html = re.sub(r"&nbsp;", " ", html)
    html = re.sub(r"&amp;", "&", html)
    html = re.sub(r"&lt;", "<", html)
    html = re.sub(r"&gt;", ">", html)
    html = re.sub(r"[ \t]+\n", "\n", html)
    html = re.sub(r"\n{3,}", "\n\n", html)
    return re.sub(r"[ \t]{2,}", " ", html).strip()
