from harness.loop import AgentLoop
from harness.permissions import PermissionGate
from harness.session import Session
from harness.tools.base import ToolSpec
from harness.tools.registry import ToolRegistry
from harness.types import LLMResponse, Message, Role, ToolCall
from harness.workspace import Workspace


class ScriptedLLM:
    def __init__(self, responses: list[LLMResponse]) -> None:
        self.responses = list(responses)

    def complete(self, messages: list[Message], tools: list[dict], on_delta=None, on_thinking=None) -> LLMResponse:
        assert messages[0].role is Role.SYSTEM
        assert isinstance(tools, list)
        response = self.responses.pop(0)
        if on_delta and response.text:
            on_delta(response.text)
        return response


class EchoTool:
    spec = ToolSpec(
        name="echo",
        description="echo",
        parameters={"type": "object", "properties": {"text": {"type": "string"}}},
    )

    def run(self, **kwargs) -> str:
        return f"echo:{kwargs.get('text', '')}"


def test_loop_tool_then_final(tmp_path):
    llm = ScriptedLLM(
        [
            LLMResponse(
                text="",
                tool_calls=[ToolCall(id="1", name="echo", arguments={"text": "hi"})],
            ),
            LLMResponse(text="done: hi"),
        ]
    )
    tools = ToolRegistry([EchoTool()])
    session = Session.start(Workspace(tmp_path))
    loop = AgentLoop(
        llm=llm,
        tools=tools,
        session=session,
        permissions=PermissionGate(tools=tools, yolo=True),
        max_turns=5,
    )
    result = loop.run("say hi")
    assert result.text == "done: hi"
    assert result.stopped_reason == "model"
    assert result.turns == 2
    roles = [m.role for m in session.messages]
    assert Role.TOOL in roles


def test_loop_unknown_tool_does_not_crash(tmp_path):
    llm = ScriptedLLM(
        [
            LLMResponse(
                text="",
                tool_calls=[ToolCall(id="1", name="nope", arguments={})],
            ),
            LLMResponse(text="gave up"),
        ]
    )
    tools = ToolRegistry([])
    session = Session.start(Workspace(tmp_path))
    loop = AgentLoop(
        llm=llm,
        tools=tools,
        session=session,
        permissions=PermissionGate(tools=tools, yolo=True),
    )
    result = loop.run("x")
    tool_msg = next(m for m in session.messages if m.role is Role.TOOL)
    assert "unknown tool" in tool_msg.content
    assert result.text == "gave up"


def test_max_turns(tmp_path):
    llm = ScriptedLLM(
        [
            LLMResponse(text="", tool_calls=[ToolCall(id="1", name="echo", arguments={"text": "a"})]),
            LLMResponse(text="", tool_calls=[ToolCall(id="2", name="echo", arguments={"text": "b"})]),
        ]
    )
    tools = ToolRegistry([EchoTool()])
    session = Session.start(Workspace(tmp_path))
    loop = AgentLoop(
        llm=llm,
        tools=tools,
        session=session,
        permissions=PermissionGate(tools=tools, yolo=True),
        max_turns=2,
    )
    result = loop.run("loop")
    assert result.stopped_reason == "max_turns"
