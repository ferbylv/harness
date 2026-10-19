from harness.tools.edit import format_edit_hunk
from harness.tui_format import (
    action_label,
    format_permission,
    parse_edit_hunk,
    parse_tool_start,
    preview_markdown,
    render_diff_markup,
)


def test_preview_markdown_closes_fence():
    assert preview_markdown("hi") == "hi"
    assert preview_markdown("```py\nprint(1)") == "```py\nprint(1)\n```"
    assert preview_markdown("```py\nprint(1)\n```") == "```py\nprint(1)\n```"


def test_format_permission_shows_full_path():
    text = format_permission(
        "write_file",
        {"path": "/Users/lvyoung/grok/harness/StrategyDemo/Pay.java", "content": "class A {}"},
    )
    assert "write_file" in text
    assert "/Users/lvyoung/grok/harness/StrategyDemo/Pay.java" in text
    assert "{'path'" not in text


def test_parse_tool_start_json():
    name, args = parse_tool_start('{"name": "read_file", "arguments": {"path": "a.py"}}')
    assert name == "read_file"
    assert args["path"] == "a.py"
    assert action_label(name, args) == "Read a.py"


def test_edit_hunk_has_line_numbers(tmp_path):
    original = "a\nkeep\nold\nkeep\n"
    hunk = format_edit_hunk("t.py", original, "old", "new")
    assert hunk.startswith("edited t.py")
    assert "-3\told" in hunk
    assert "+3\tnew" in hunk
    parsed = parse_edit_hunk(hunk)
    assert parsed is not None
    path, rows = parsed
    assert path == "t.py"
    ops = {op: body for op, _n, body in rows}
    assert ops["-"] == "old"
    assert ops["+"] == "new"
    markup = render_diff_markup(hunk)
    assert markup is not None
    assert "old" in markup
    assert "new" in markup
