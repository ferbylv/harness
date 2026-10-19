from __future__ import annotations

import json
import sys

from harness.loop import LoopResult
from harness.runtime import Runtime
from harness.session import Session
from harness.tui_format import format_permission
from harness.types import ToolCall


class EventPrinter:
    def __init__(self) -> None:
        self._mode: str | None = None

    def __call__(self, kind: str, payload: str) -> None:
        if kind == "status":
            self.close()
            print(f"  … {payload}")
            return
        if kind == "thinking_delta":
            self._open("think")
            print(payload, end="", flush=True)
            return
        if kind == "text_delta":
            self._open("agent")
            print(payload, end="", flush=True)
            return
        if kind == "assistant_end":
            self.close()
            return
        if kind == "tool_start":
            self.close()
            print(f"  → {_tool_start_label(payload)}")
            return
        if kind == "tool_end":
            preview = payload if len(payload) < 400 else payload[:400] + " …"
            for line in preview.splitlines()[:12]:
                print(f"    {line}")

    def _open(self, mode: str) -> None:
        if self._mode == mode:
            return
        if self._mode:
            print("\n", flush=True)
        print(f"\n{mode}>\n", end="", flush=True)
        self._mode = mode

    def close(self) -> None:
        if self._mode:
            print("\n", flush=True)
            self._mode = None


def _tool_start_label(payload: str) -> str:
    try:
        data = json.loads(payload)
        name = data.get("name") or "tool"
        args = data.get("arguments") or {}
        return f"{name} {args}".strip()
    except json.JSONDecodeError:
        return payload


def confirm(call: ToolCall | str) -> bool | str:
    if not sys.stdin.isatty():
        return False
    if isinstance(call, str):
        prompt = call
    else:
        print()
        print(format_permission(call.name, call.arguments))
        print()
        print("  y allow once  ·  a always this tool  ·  A allow all  ·  n deny")
        prompt = "> "
    try:
        choice = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        return False
    if choice in {"y", "yes"}:
        return "once"
    if choice == "a":
        return "always_tool"
    if choice == "A":
        return "always"
    return False


def run_once(runtime: Runtime, prompt: str) -> int:
    printer = EventPrinter()
    runtime.loop.on_event = printer
    result = runtime.submit(prompt)
    printer.close()
    _print_usage(runtime.session, result)
    if result.stopped_reason == "cancelled":
        print("(cancelled)")
    elif not result.text:
        print(f"[{result.stopped_reason} after {result.turns} turns]")
    return 0


def run_repl(runtime: Runtime) -> int:
    printer = EventPrinter()
    runtime.loop.on_event = printer
    if runtime.loop.permissions.ask is None:
        runtime.loop.permissions.ask = confirm
    print("harness  (type a task, or /help)")
    print(f"workspace: {runtime.workspace.root}")
    print(f"model:     {runtime.model_label()}")
    print(f"session:   {runtime.session.id}")
    if runtime.skills:
        print(f"skills:    {', '.join(s.name for s in runtime.skills)}")
    print()
    while True:
        try:
            line = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            runtime.persist()
            return 0
        if not line:
            continue
        outcome = runtime.handle_command(line)
        if outcome.switch_ui:
            if outcome.notice:
                print(outcome.notice)
            return 0
        if outcome.quit:
            return 0
        if outcome.handled:
            if outcome.notice:
                print(outcome.notice)
            continue
        try:
            result = runtime.submit(line)
        except KeyboardInterrupt:
            printer.close()
            print("(cancelled)")
            runtime.persist()
            continue
        printer.close()
        if result.stopped_reason == "cancelled":
            print("(cancelled)")
        _print_usage(runtime.session, result)


def _print_usage(session: Session, result: LoopResult) -> None:
    extra = "  compacted" if result.compacted else ""
    cost = f"  ${session.cost_usd:.4f}" if session.cost_usd else ""
    print(
        f"  tokens ↑{result.usage.prompt_tokens} ↓{result.usage.completion_tokens}"
        f"  session ↑{session.prompt_tokens} ↓{session.completion_tokens}{cost}{extra}"
    )
