import asyncio
from pathlib import Path

from textual.widgets import Static

from harness.config import Config
from harness.runtime import Runtime
from harness.tui import HarnessTUI
from harness.ui.classic import ClassicTUI
from harness.ui.glass import GlassTUI


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


def test_transcript_tracks_bottom_when_content_overflows(tmp_path):
    rt = Runtime(config=_config(tmp_path), persist=False, ask=lambda _p: True)
    app = HarnessTUI(rt)

    async def _run():
        async with app.run_test(size=(80, 20)) as pilot:
            log = app.transcript
            assert log.is_anchored
            for i in range(60):
                log.mount(Static(f"row {i} " + "x" * 40, classes="notice"))
            await pilot.pause()
            assert log.max_scroll_y > 0
            assert log.is_vertical_scroll_end
            app._append_live("agent", "\n\n".join(f"paragraph {i}" for i in range(40)))
            await pilot.pause()
            await pilot.pause()
            assert log.is_vertical_scroll_end

    asyncio.run(_run())


def test_tui_mounts_and_help(tmp_path):
    rt = Runtime(config=_config(tmp_path), persist=False, ask=lambda _p: True)
    app = HarnessTUI(rt)

    async def _run():
        async with app.run_test() as pilot:
            assert app.query_one("#composer")
            assert app.query_one("#log")
            perm = app.query_one("#permission")
            assert perm.display is False
            await pilot.click("#composer")
            app.action_help()
            assert "compact" in app.rt.handle_command("/help").notice

    asyncio.run(_run())


def test_classic_tui_mounts(tmp_path):
    rt = Runtime(config=_config(tmp_path), persist=False, ask=lambda _p: True)
    app = ClassicTUI(rt)

    async def _run():
        async with app.run_test() as pilot:
            del pilot
            assert app.query_one("#composer")
            assert app.query_one("#log")
            assert app.query_one("#permission").display is False

    asyncio.run(_run())


def test_glass_tui_mounts(tmp_path):
    rt = Runtime(config=_config(tmp_path), persist=False, ask=lambda _p: True)
    app = GlassTUI(rt)

    async def _run():
        async with app.run_test() as pilot:
            del pilot
            assert app.query_one("#composer")
            assert app.palette.name == "glass"

    asyncio.run(_run())
