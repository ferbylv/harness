from pathlib import Path

import httpx
import pytest

from harness.config import Config
from harness.permissions import PermissionGate
from harness.tools import default_tools
from harness.tools.edit import EditFile
from harness.tools.web_fetch import WebFetch
from harness.types import ToolCall
from harness.workspace import Workspace


def _config(root: Path) -> Config:
    return Config(
        workspace=root,
        provider="mock",
        model="mock",
        base_url="",
        api_key="",
        mock=True,
        yolo=True,
        stream=True,
        max_turns=5,
        max_tool_output=10_000,
        compact_at=32_000,
        keep_last=16,
        compact_summarize=False,
        reasoning=True,
    )


def test_workspace_blocks_escape(tmp_path):
    ws = Workspace(tmp_path)
    with pytest.raises(PermissionError):
        ws.resolve("../outside.txt")


def test_read_write_edit_roundtrip(tmp_path):
    ws = Workspace(tmp_path)
    tools = default_tools(ws, _config(tmp_path))
    tools.dispatch(ToolCall(id="w", name="write_file", arguments={"path": "a.py", "content": "x = 1\n"}))
    listed = tools.dispatch(ToolCall(id="l", name="list_dir", arguments={"path": "."}))
    assert "a.py" in listed
    read = tools.dispatch(ToolCall(id="r", name="read_file", arguments={"path": "a.py"}))
    assert "x = 1" in read
    edited = tools.dispatch(
        ToolCall(
            id="e",
            name="edit_file",
            arguments={"path": "a.py", "old_string": "x = 1", "new_string": "x = 2"},
        )
    )
    assert "edited" in edited
    assert (tmp_path / "a.py").read_text() == "x = 2\n"


def test_edit_requires_unique_match(tmp_path):
    ws = Workspace(tmp_path)
    path = tmp_path / "dup.txt"
    path.write_text("aa\naa\n")
    out = EditFile(ws).run(path="dup.txt", old_string="aa", new_string="bb")
    assert "2 times" in out


def test_grep_finds_line(tmp_path):
    (tmp_path / "hit.py").write_text("def hello():\n    return 1\n")
    tools = default_tools(Workspace(tmp_path), _config(tmp_path))
    out = tools.dispatch(ToolCall(id="g", name="grep", arguments={"pattern": "def hello", "glob": "*.py"}))
    assert "hit.py:1:" in out


def test_permission_denies_mutating_when_ask_false(tmp_path):
    tools = default_tools(Workspace(tmp_path), _config(tmp_path))
    gate = PermissionGate(tools=tools, yolo=False, ask=lambda _p: False)
    allowed, reason = gate.allow(ToolCall(id="1", name="bash", arguments={"command": "echo hi"}))
    assert not allowed
    assert reason == "user denied"
    allowed, _ = gate.allow(ToolCall(id="2", name="read_file", arguments={"path": "x"}))
    assert allowed
    allowed, _ = gate.allow(ToolCall(id="3", name="web_fetch", arguments={"url": "https://example.com"}))
    assert allowed


def test_permission_always_tool_remembers(tmp_path):
    tools = default_tools(Workspace(tmp_path), _config(tmp_path))
    answers = iter(["always_tool"])
    gate = PermissionGate(tools=tools, yolo=False, ask=lambda _c: next(answers))
    first = ToolCall(id="1", name="write_file", arguments={"path": "a", "content": "x"})
    allowed, reason = gate.allow(first)
    assert allowed
    assert reason == "always this tool"
    allowed, reason = gate.allow(first)
    assert allowed
    assert reason == "session tool"


def test_web_fetch_rejects_non_http():
    tool = WebFetch()
    assert "only http/https" in tool.run(url="file:///etc/passwd")
    assert "url host is missing" in tool.run(url="https://")


def test_web_fetch_reads_html_and_json():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/page":
            return httpx.Response(
                200,
                headers={"content-type": "text/html"},
                text="<html><script>x()</script><p>Beijing 18C</p></html>",
            )
        if request.url.path == "/api":
            return httpx.Response(
                200,
                headers={"content-type": "application/json"},
                json={"temp": 18},
            )
        return httpx.Response(404, text="missing")

    tool = WebFetch(client=httpx.Client(transport=httpx.MockTransport(handler)))
    html = tool.run(url="https://example.test/page")
    assert "Beijing 18C" in html
    assert "x()" not in html
    assert "HTTP 200" in html
    data = tool.run(url="https://example.test/api")
    assert '"temp": 18' in data
