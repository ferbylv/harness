from pathlib import Path

from harness.config import Config
from harness.runtime import Runtime


def _config(root: Path) -> Config:
    return Config(
        workspace=root,
        provider="mock",
        model="mock-model",
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


def test_commands_help_and_model(tmp_path):
    rt = Runtime(config=_config(tmp_path), persist=False, ask=lambda _p: True)
    help_out = rt.handle_command("/help")
    assert help_out.handled
    assert "/compact" in help_out.notice
    assert rt.handle_command("/model").notice == "mock-model"
    switched = rt.handle_command("/model other")
    assert switched.notice == "model other"
    assert rt.model_name() == "other"
    assert rt.handle_command("plain text").handled is False
    assert rt.handle_command("/quit").quit is True


def test_tui_command_lists_and_switches(tmp_path):
    from harness.ui import load_builtins, names

    load_builtins()
    rt = Runtime(config=_config(tmp_path), persist=False)
    listed = rt.handle_command("/tui")
    assert listed.handled
    assert "textual" in listed.notice
    assert "classic" in listed.notice
    assert "glass" in listed.notice
    switched = rt.handle_command("/tui repl")
    assert switched.switch_ui == "repl"
    assert rt.switch_ui == "repl"
    bad = rt.handle_command("/tui does-not-exist")
    assert bad.switch_ui is None
    assert "unknown ui" in bad.notice
    assert set(names()) >= {"textual", "repl"}


def test_reset_changes_session_id(tmp_path):
    rt = Runtime(config=_config(tmp_path), persist=False)
    old = rt.session.id
    rt.handle_command("/reset")
    assert rt.session.id != old
    assert rt.session.messages == []
