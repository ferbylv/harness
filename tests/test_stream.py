from harness.llm.openai_compat import merge_tool_delta, _sse_data, _slot_to_call
from harness.types import parse_usage
from harness.loop import AgentLoop
from harness.permissions import PermissionGate
from harness.session import Session
from harness.tools.registry import ToolRegistry
from harness.types import LLMResponse, Message, Role
from harness.workspace import Workspace


class StreamingLLM:
    def complete(self, messages, tools, on_delta=None, on_thinking=None):
        assert messages[0].role is Role.SYSTEM
        text = "hello world"
        if on_delta:
            on_delta("hello ")
            on_delta("world")
        return LLMResponse(text=text)


def test_loop_emits_text_deltas(tmp_path):
    events: list[tuple[str, str]] = []
    tools = ToolRegistry([])
    loop = AgentLoop(
        llm=StreamingLLM(),
        tools=tools,
        session=Session.start(Workspace(tmp_path)),
        permissions=PermissionGate(tools=tools, yolo=True),
        on_event=lambda kind, payload: events.append((kind, payload)),
    )
    result = loop.run("hi")
    assert result.text == "hello world"
    assert ("text_delta", "hello ") in events
    assert ("text_delta", "world") in events
    assert events[-1][0] == "assistant_end"


def test_merge_streamed_tool_call():
    slots: dict[int, dict[str, str]] = {}
    merge_tool_delta(slots, {"index": 0, "id": "call_1", "function": {"name": "bash", "arguments": ""}})
    merge_tool_delta(slots, {"index": 0, "function": {"arguments": "{\"command\":"}})
    merge_tool_delta(slots, {"index": 0, "function": {"arguments": "\"ls\"}"}})
    call = _slot_to_call(slots[0])
    assert call.id == "call_1"
    assert call.name == "bash"
    assert call.arguments == {"command": "ls"}


def test_parse_usage_openrouter_shape():
    usage = parse_usage({"usage": {"prompt_tokens": 11, "completion_tokens": 7, "cost": 0.002}})
    assert usage.prompt_tokens == 11
    assert usage.completion_tokens == 7
    assert usage.cost_usd == 0.002


def test_sse_data_parser():
    assert _sse_data("data: {\"a\":1}") == '{"a":1}'
    assert _sse_data("data: [DONE]") == "[DONE]"
    assert _sse_data("") is None
    assert _sse_data(": keep-alive") is None
