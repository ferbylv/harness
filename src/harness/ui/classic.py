from __future__ import annotations

from harness.runtime import Runtime
from harness.tui import HarnessTUI
from harness.ui.theme import PHOSPHOR, css_from_theme


class ClassicTUI(HarnessTUI):
    """Same features as textual; green-phosphor colors only."""

    TITLE = "classic"
    PALETTE = PHOSPHOR
    CSS = css_from_theme(PHOSPHOR)


def run_classic(runtime: Runtime) -> int:
    return ClassicTUI(runtime).run() or 0
