from harness.llm.thinking import ThinkSplitter, extract_thinking
from harness.loop import AgentLoop
from harness.permissions import PermissionGate
from harness.session import Session
from harness.tools.registry import ToolRegistry
from harness.types import LLMResponse, Role
from harness.workspace import Workspace


def test_extract_thinking_fields():
    assert extract_thinking({"reasoning_content": "step 1"}) == "step 1"
    assert extract_thinking({"reasoning": {"content": "hidden"}}) == "hidden"
    assert extract_thinking({"content": "hi"}) == ""


def test_think_splitter_handles_partial_tags():
    splitter = ThinkSplitter()
    events = []
    events.extend(splitter.feed("<thi"))
    events.extend(splitter.feed("nk>plan"))
    events.extend(splitter.feed("</th"))
    events.extend(splitter.feed("ink>answer"))
    events.extend(splitter.flush())
    kinds = [(k, t) for k, t in events if t]
    assert ("thinking", "plan") in kinds
    assert ("text", "answer") in kinds


def test_loop_emits_thinking_deltas(tmp_path):
    class LLM:
        def complete(self, messages, tools, on_delta=None, on_thinking=None):
            assert messages[0].role is Role.SYSTEM
            if on_thinking:
                on_thinking("consider files")
            if on_delta:
                on_delta("done")
            return LLMResponse(text="done", thinking="consider files")

    events: list[tuple[str, str]] = []
    tools = ToolRegistry([])
    loop = AgentLoop(
        llm=LLM(),
        tools=tools,
        session=Session.start(Workspace(tmp_path)),
        permissions=PermissionGate(tools=tools, yolo=True),
        on_event=lambda kind, payload: events.append((kind, payload)),
    )
    result = loop.run("hi")
    assert result.text == "done"
    assert ("thinking_delta", "consider files") in events
    assert ("text_delta", "done") in events
    # thinking is not stored as the assistant reply
    assistant = [m for m in loop.session.messages if m.role is Role.ASSISTANT][0]
    assert assistant.content == "done"
