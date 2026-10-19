from harness.cancel import CancelToken, Cancelled
from harness.loop import AgentLoop
from harness.permissions import PermissionGate
from harness.session import Session
from harness.tools.registry import ToolRegistry
from harness.types import LLMResponse, Role
from harness.workspace import Workspace


def test_loop_stops_when_cancelled(tmp_path):
    token = CancelToken()

    class LLM:
        def complete(self, messages, tools, on_delta=None, on_thinking=None):
            token.cancel()
            token.throw_if_set()
            return LLMResponse(text="should not reach")

    tools = ToolRegistry([])
    loop = AgentLoop(
        llm=LLM(),
        tools=tools,
        session=Session.start(Workspace(tmp_path)),
        permissions=PermissionGate(tools=tools, yolo=True),
        cancel=token,
    )
    result = loop.run("stop me")
    assert result.stopped_reason == "cancelled"
    assert any(m.role is Role.USER for m in loop.session.messages)


def test_cancel_token_raises():
    token = CancelToken()
    token.cancel()
    try:
        token.throw_if_set()
    except Cancelled:
        return
    raise AssertionError("expected Cancelled")
