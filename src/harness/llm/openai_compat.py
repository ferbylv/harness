from __future__ import annotations

import json
import time
from typing import Any

import httpx

from harness.cancel import CancelToken, Cancelled
from harness.llm.thinking import ThinkSplitter, extract_thinking
from harness.types import DeltaFn, LLMResponse, Message, ToolCall, parse_usage


class OpenAICompatClient:
    """Talks to any OpenAI-compatible /chat/completions endpoint (xAI, OpenAI, local)."""

    def __init__(
        self,
        *,
        base_url: str,
        api_key: str,
        model: str,
        timeout: float = 120.0,
        stream: bool = True,
        include_reasoning: bool = False,
        cancel: CancelToken | None = None,
        max_retries: int = 3,
    ) -> None:
        if not api_key:
            raise RuntimeError("missing API key.")
        self.model = model
        self.stream = stream
        self.include_reasoning = include_reasoning
        self.cancel = cancel
        self.max_retries = max(0, max_retries)
        self._base_url = base_url
        self._api_key = api_key
        self._timeout = timeout
        self._client = self._make_client()

    def _make_client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(self._timeout, connect=30.0),
        )

    def _force_close(self) -> None:
        old = self._client
        try:
            old.close()
        except Exception:
            pass
        self._client = self._make_client()

    def complete(
        self,
        messages: list[Message],
        tools: list[dict],
        on_delta: DeltaFn | None = None,
        on_thinking: DeltaFn | None = None,
    ) -> LLMResponse:
        body: dict[str, Any] = {
            "model": self.model,
            "messages": [m.to_openai() for m in messages],
            "stream": self.stream,
        }
        if tools:
            body["tools"] = tools
            body["tool_choice"] = "auto"
        if self.include_reasoning:
            body["reasoning"] = {"enabled": True, "exclude": False}
        if self.stream:
            body["stream_options"] = {"include_usage": True}
        if self.cancel:
            self.cancel.set_close(self._force_close)
        return self._retry(lambda: self._dispatch(body, on_delta, on_thinking))

    def _dispatch(
        self,
        body: dict[str, Any],
        on_delta: DeltaFn | None,
        on_thinking: DeltaFn | None,
    ) -> LLMResponse:
        try:
            if self.stream:
                return self._complete_stream(body, on_delta, on_thinking)
            return self._complete_once(body, on_delta, on_thinking)
        except RuntimeError as exc:
            if self.include_reasoning and "HTTP 400" in str(exc):
                body.pop("reasoning", None)
                self.include_reasoning = False
                if self.stream:
                    return self._complete_stream(body, on_delta, on_thinking)
                return self._complete_once(body, on_delta, on_thinking)
            raise

    def _retry(self, fn):
        delay = 1.0
        last: Exception | None = None
        for attempt in range(self.max_retries + 1):
            self._check()
            try:
                return fn()
            except Cancelled:
                raise
            except RuntimeError as exc:
                last = exc
                if not _is_retryable(exc) or attempt >= self.max_retries:
                    raise
                self._sleep(delay)
                delay = min(delay * 2, 16)
        raise last or RuntimeError("retry failed")

    def _check(self) -> None:
        if self.cancel:
            self.cancel.throw_if_set()

    def _sleep(self, seconds: float) -> None:
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            self._check()
            time.sleep(min(0.2, deadline - time.monotonic()))

    def _complete_once(
        self,
        body: dict[str, Any],
        on_delta: DeltaFn | None,
        on_thinking: DeltaFn | None,
    ) -> LLMResponse:
        response = self._client.post("/chat/completions", json=body)
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise _http_error(exc, self.model) from exc
        data = response.json()
        choice = data["choices"][0]["message"]
        raw_text = choice.get("content") or ""
        thinking_parts = [extract_thinking(choice)]
        splitter = ThinkSplitter()
        text_parts: list[str] = []
        for kind, piece in [*splitter.feed(raw_text), *splitter.flush()]:
            if kind == "thinking":
                thinking_parts.append(piece)
            else:
                text_parts.append(piece)
        thinking = "".join(p for p in thinking_parts if p)
        text = "".join(text_parts)
        if on_thinking and thinking:
            on_thinking(thinking)
        if on_delta and text:
            on_delta(text)
        tool_calls = [_parse_tool_call(raw) for raw in choice.get("tool_calls") or []]
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            raw=data,
            usage=parse_usage(data),
            thinking=thinking,
        )

    def _complete_stream(
        self,
        body: dict[str, Any],
        on_delta: DeltaFn | None,
        on_thinking: DeltaFn | None,
    ) -> LLMResponse:
        text_parts: list[str] = []
        thinking_parts: list[str] = []
        slots: dict[int, dict[str, str]] = {}
        usage = parse_usage({})
        last_raw: dict[str, Any] = {}
        splitter = ThinkSplitter()

        def _emit(kind: str, piece: str) -> None:
            if not piece:
                return
            if kind == "thinking":
                thinking_parts.append(piece)
                if on_thinking:
                    on_thinking(piece)
            else:
                text_parts.append(piece)
                if on_delta:
                    on_delta(piece)
        with self._client.stream("POST", "/chat/completions", json=body) as response:
            if self.cancel:
                self.cancel.set_close(response.close)
            if response.status_code >= 400:
                raw = response.read().decode("utf-8", errors="replace")
                raise RuntimeError(_http_error_from_body(response.status_code, raw, self.model))
            try:
                for line in response.iter_lines():
                    self._check()
                    payload = _sse_data(line)
                    if payload is None:
                        continue
                    if payload == "[DONE]":
                        break
                    try:
                        chunk = json.loads(payload)
                    except json.JSONDecodeError:
                        continue
                    if chunk.get("error"):
                        raise RuntimeError(
                            _http_error_from_body(
                                429 if _is_rate_limit(chunk) else 500, payload, self.model
                            )
                        )
                    last_raw = chunk
                    chunk_usage = parse_usage(chunk)
                    if chunk_usage.total_tokens or chunk_usage.cost_usd:
                        usage = chunk_usage
                    choice = (chunk.get("choices") or [{}])[0]
                    delta = choice.get("delta") or {}
                    thought = extract_thinking(delta)
                    if thought:
                        _emit("thinking", thought)
                    for kind, piece in splitter.feed(delta.get("content") or ""):
                        _emit(kind, piece)
                    for raw in delta.get("tool_calls") or []:
                        merge_tool_delta(slots, raw)
            except Cancelled:
                raise
            except Exception:
                if self.cancel and self.cancel.is_set():
                    raise Cancelled()
                raise
        for kind, piece in splitter.flush():
            _emit(kind, piece)
        text = "".join(text_parts)
        tool_calls = [_slot_to_call(slots[i]) for i in sorted(slots)]
        return LLMResponse(
            text=text,
            tool_calls=tool_calls,
            raw=last_raw,
            usage=usage,
            thinking="".join(thinking_parts),
        )


def _is_retryable(exc: BaseException) -> bool:
    text = str(exc).lower()
    return "http 429" in text or "rate-limited" in text or "rate_limit" in text


def merge_tool_delta(slots: dict[int, dict[str, str]], raw: dict[str, Any]) -> None:
    idx = int(raw.get("index") or 0)
    slot = slots.setdefault(idx, {"id": "", "name": "", "arguments": ""})
    if raw.get("id"):
        slot["id"] = str(raw["id"])
    fn = raw.get("function") or {}
    if fn.get("name"):
        slot["name"] += str(fn["name"])
    if fn.get("arguments"):
        slot["arguments"] += str(fn["arguments"])


def _slot_to_call(slot: dict[str, str]) -> ToolCall:
    return _parse_tool_call(
        {
            "id": slot["id"],
            "function": {"name": slot["name"], "arguments": slot["arguments"] or "{}"},
        }
    )


def _sse_data(line: str) -> str | None:
    if not line or line.startswith(":"):
        return None
    if not line.startswith("data:"):
        return None
    return line[5:].strip()


def _is_rate_limit(chunk: dict[str, Any]) -> bool:
    err = chunk.get("error")
    if not isinstance(err, dict):
        return False
    return err.get("code") == 429 or "rate" in str(err.get("message") or "").lower()


def _http_error(exc: httpx.HTTPStatusError, model: str) -> RuntimeError:
    return RuntimeError(_http_error_from_body(exc.response.status_code, exc.response.text, model))


def _http_error_from_body(status: int, body: str, model: str) -> str:
    detail = _error_detail(body)
    if status == 429:
        return (
            f"rate-limited (HTTP 429) on {model!r}. {detail} "
            "wait a bit, switch HARNESS_MODEL, or use a paid / BYOK route on OpenRouter."
        )
    if status in {401, 403}:
        return f"auth failed (HTTP {status}) for {model!r}. {detail}"
    return f"LLM HTTP {status}: {detail}"


def _error_detail(body: str) -> str:
    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return body[:500]
    err = data.get("error") if isinstance(data, dict) else None
    if not isinstance(err, dict):
        return body[:500]
    parts = [str(err.get("message") or "").strip()]
    meta = err.get("metadata") if isinstance(err.get("metadata"), dict) else {}
    raw = str(meta.get("raw") or "").strip()
    if raw and raw not in parts[0]:
        parts.append(raw)
    return " ".join(p for p in parts if p) or body[:500]


def _parse_tool_call(raw: dict[str, Any]) -> ToolCall:
    fn = raw.get("function") or {}
    arguments = fn.get("arguments") or "{}"
    if isinstance(arguments, str):
        try:
            parsed = json.loads(arguments or "{}")
        except json.JSONDecodeError:
            parsed = {"_raw": arguments}
    else:
        parsed = arguments
    if not isinstance(parsed, dict):
        parsed = {"value": parsed}
    return ToolCall(id=raw.get("id") or "", name=fn.get("name") or "", arguments=parsed)
