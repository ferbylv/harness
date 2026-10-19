from __future__ import annotations

import argparse
import os
import sys

from harness.repl import confirm, run_once
from harness.runtime import Runtime
from harness.ui import load_builtins, load_plugin, names, run_ui


def main(argv: list[str] | None = None) -> int:
    args = _parse(argv)
    load_builtins()
    for spec in _plugin_specs():
        load_plugin(spec)
    if args.list_ui:
        for name in names():
            print(name)
        return 0
    runtime = Runtime.from_args(args, ask=confirm)
    if args.prompt:
        return run_once(runtime, args.prompt)
    current = _pick_ui(args)
    while True:
        runtime.switch_ui = None
        run_ui(current, runtime)
        nxt = runtime.switch_ui
        if not nxt:
            return 0
        current = nxt


def _plugin_specs() -> list[str]:
    raw = os.getenv("HARNESS_UI_PLUGIN", "").strip()
    if not raw:
        return []
    return [item.strip() for item in raw.split(",") if item.strip()]


def _pick_ui(args: argparse.Namespace) -> str:
    if args.repl:
        return "repl"
    if args.tui:
        return "textual"
    if args.ui:
        return args.ui
    env = os.getenv("HARNESS_UI", "").strip()
    if env:
        return env
    flag = os.getenv("HARNESS_TUI", "").strip().lower()
    if flag in {"0", "false", "no", "off"}:
        return "repl"
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        return "repl"
    return "textual"


def _parse(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="harness", description="A small coding-agent harness.")
    parser.add_argument("prompt", nargs="?", help="Run one turn non-interactively, then exit.")
    parser.add_argument("-w", "--workspace", help="Project root. Default: cwd.")
    parser.add_argument("--continue", dest="continue_session", action="store_true", help="Resume the latest session.")
    parser.add_argument("--resume", metavar="ID", help="Resume a saved session by id.")
    parser.add_argument("--no-session", action="store_true", help="Do not write .harness/sessions.")
    parser.add_argument("--ui", metavar="NAME", help="Front-end: textual | repl | a registered plugin.")
    parser.add_argument("--list-ui", action="store_true", help="Print registered front-ends and exit.")
    parser.add_argument("--tui", action="store_true", help="Same as --ui textual.")
    parser.add_argument("--repl", action="store_true", help="Same as --ui repl.")
    return parser.parse_args(argv)
