import sys
import types

from harness.runtime import Runtime
from harness.ui import EVENT_KINDS, UserInterface, get, load_builtins, load_plugin, names, register, run_ui
from harness.ui.registry import _FRONTENDS


def setup_function() -> None:
    _FRONTENDS.clear()


def test_register_and_run(tmp_path):
    seen: list[str] = []

    def fake(runtime: Runtime) -> int:
        seen.append(runtime.session.id)
        return 7

    register("fake", fake, description="test double")
    assert "fake" in names()
    from harness.config import Config

    config = Config(
        workspace=tmp_path,
        provider="mock",
        model="m",
        base_url="",
        api_key="",
        mock=True,
        yolo=True,
        stream=True,
        max_turns=3,
        max_tool_output=1000,
        compact_at=32_000,
        keep_last=8,
        compact_summarize=False,
        reasoning=False,
    )
    rt = Runtime(config=config, persist=False)
    assert run_ui("fake", rt) == 7
    assert seen == [rt.session.id]


def test_protocol_object_is_accepted():
    class Dummy:
        name = "dummy"

        def run(self, runtime: Runtime) -> int:
            del runtime
            return 0

    ui = Dummy()
    assert isinstance(ui, UserInterface)
    register("dummy", ui.run)
    assert get("dummy").name == "dummy"


def test_load_plugin_registers_callable():
    mod = types.ModuleType("harness_ui_plugin_test")

    def run(runtime: Runtime) -> int:
        del runtime
        return 3

    mod.run = run  # type: ignore[attr-defined]
    sys.modules["harness_ui_plugin_test"] = mod
    name = load_plugin("harness_ui_plugin_test:run")
    assert name
    from harness.config import Config

    rt = Runtime(
        config=Config(
            workspace=__import__("pathlib").Path("."),
            provider="mock",
            model="m",
            base_url="",
            api_key="",
            mock=True,
            yolo=True,
            stream=True,
            max_turns=1,
            max_tool_output=100,
            compact_at=1000,
            keep_last=4,
            compact_summarize=False,
            reasoning=False,
        ),
        persist=False,
    )
    assert run_ui(name, rt) == 3


def test_builtins_include_textual_and_repl():
    load_builtins()
    assert set(names()) >= {"textual", "classic", "glass", "repl"}
    assert "text_delta" in EVENT_KINDS
    assert "tool_start" in EVENT_KINDS
