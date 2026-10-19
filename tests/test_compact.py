from harness.compact import should_compact, split_for_compact
from harness.loop import AgentLoop
from harness.permissions import PermissionGate
from harness.session import Session
from harness.tools.registry import ToolRegistry
from harness.types import LLMResponse, Message, Role, Usage
from harness.workspace import Workspace


def test_split_snaps_to_user_turn():
    messages = [
        Message(role=Role.USER, content="one"),
        Message(role=Role.ASSISTANT, content="ok"),
        Message(role=Role.USER, content="two"),
        Message(role=Role.ASSISTANT, content="", tool_calls=[]),
        Message(role=Role.TOOL, content="r", tool_call_id="1"),
        Message(role=Role.USER, content="three"),
        Message(role=Role.ASSISTANT, content="done"),
    ]
    prefix, tail = split_for_compact(messages, keep_last=2)
    assert tail[0].content == "three"
    assert prefix[-1].role is Role.TOOL


def test_should_compact_uses_usage_first():
    msgs = [Message(role=Role.USER, content="x")]
    assert should_compact(msgs, last_prompt_tokens=40_000, compact_at=32_000)
    assert not should_compact(msgs, last_prompt_tokens=10, compact_at=32_000)


def test_loop_compacts_before_next_complete(tmp_path):
    class LLM:
        def __init__(self):
            self.seen = []

        def complete(self, messages, tools, on_delta=None, on_thinking=None):
            self.seen.append([m.content for m in messages if m.role is Role.USER])
            return LLMResponse(text="ok", usage=Usage(prompt_tokens=100, completion_tokens=1))

    llm = LLM()
    session = Session.start(Workspace(tmp_path))
    for i in range(6):
        session.add(Message(role=Role.USER, content=f"u{i}"))
        session.add(Message(role=Role.ASSISTANT, content=f"a{i}"))
    session.last_prompt_tokens = 99
    tools = ToolRegistry([])
    loop = AgentLoop(
        llm=llm,
        tools=tools,
        session=session,
        permissions=PermissionGate(tools=tools, yolo=True),
        compact_at=50,
        keep_last=4,
        compact_summarize=False,
    )
    result = loop.run("next")
    assert result.compacted
    assert any("compacted" in c for batch in llm.seen for c in batch)
    assert session.messages[0].role is Role.USER
