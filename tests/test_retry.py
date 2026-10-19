import httpx

from harness.llm.openai_compat import OpenAICompatClient, _is_retryable
from harness.types import Message, Role


def test_is_retryable():
    assert _is_retryable(RuntimeError("rate-limited (HTTP 429) on 'x'"))
    assert not _is_retryable(RuntimeError("auth failed (HTTP 401)"))


def test_retries_then_succeeds(monkeypatch):
    hits = {"n": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        hits["n"] += 1
        if hits["n"] < 3:
            return httpx.Response(429, json={"error": {"message": "rate"}})
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "ok", "tool_calls": []}}]},
        )

    client = OpenAICompatClient(
        base_url="https://example.test/v1",
        api_key="x",
        model="m",
        stream=False,
        include_reasoning=False,
        max_retries=3,
    )
    client._client = httpx.Client(
        transport=httpx.MockTransport(handler),
        base_url="https://example.test/v1",
    )
    monkeypatch.setattr(client, "_sleep", lambda _s: None)
    response = client.complete([Message(role=Role.USER, content="hi")], [])
    assert response.text == "ok"
    assert hits["n"] == 3
