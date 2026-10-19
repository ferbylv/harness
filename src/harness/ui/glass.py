from __future__ import annotations

from harness.runtime import Runtime
from harness.tui import HarnessTUI
from harness.ui.theme import FROST, GLASS_EXTRA, css_from_theme


class GlassTUI(HarnessTUI):
    """Same features as textual; icy frosted-glass colors."""

    TITLE = "glass"
    PALETTE = FROST
    CSS = css_from_theme(FROST) + GLASS_EXTRA


def run_glass(runtime: Runtime) -> int:
    return GlassTUI(runtime).run() or 0
