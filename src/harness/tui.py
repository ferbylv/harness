from __future__ import annotations

import os
import queue
import threading
import time
from pathlib import Path

from rich.markup import escape
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual import events
from textual.containers import Vertical, VerticalScroll
from textual.message import Message
from textual.widgets import Markdown, Static, TextArea

from harness.clipboard import image_paths_in_paste, read_clipboard_image
from harness.content import has_images, text_of
from harness.draft import LARGE_PASTE, Draft
from harness.runtime import Runtime
from harness.tui_format import (
    action_label,
    lexer_for,
    parse_edit_hunk,
    parse_tool_start,
    preview_markdown,
    render_diff_line,
)
from harness.types import Role, ToolCall
from harness.ui.theme import PI, Theme, css_from_theme

_LIVE_CAP = 8_000
_SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"


def _short_path(path: Path) -> str:
    home = Path.home()
    try:
        return "~/" + str(path.resolve().relative_to(home))
    except ValueError:
        return str(path)


def _fmt_n(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}m"
    if n >= 1000:
        return f"{n / 1000:.1f}k"
    return str(n)


class ChoiceCard(Static):
    def __init__(self, index: int) -> None:
        super().__init__("", classes="choice", id=f"perm-opt-{index}")
        self.index = index


class PermissionBar(Vertical, can_focus=True):
    """Radio-card ask, aligned above the composer."""

    BINDINGS = [
        Binding("up", "move(-1)", show=False),
        Binding("down", "move(1)", show=False),
        Binding("k", "move(-1)", show=False),
        Binding("j", "move(1)", show=False),
        Binding("enter", "confirm", show=False),
        Binding("y", "pick('once')", show=False),
        Binding("a", "pick('always_tool')", show=False),
        Binding("n", "pick('deny')", show=False),
        Binding("escape", "pick('deny')", show=False),
    ]

    def __init__(self) -> None:
        super().__init__(id="permission")
        self._box: queue.Queue[bool | str] | None = None
        self._index = 0
        self._choices: list[tuple[str, str, str]] = []
        self.display = False

    def compose(self) -> ComposeResult:
        yield Static("", id="perm-question")
        with Vertical(id="perm-options"):
            for i in range(4):
                yield ChoiceCard(i)

    def present(self, call: ToolCall, box: queue.Queue[bool | str]) -> None:
        self._box = box
        self._index = 0
        name = call.name
        verb = action_label(name, call.arguments)
        self._choices = [
            ("once", "once", "y"),
            ("always_tool", f"always {name}", "a"),
            ("always", "allow all", "A"),
            ("deny", "deny", "n"),
        ]
        accent = getattr(type(self.app), "PALETTE", PI).accent
        self.query_one("#perm-question", Static).update(
            f"[bold {accent}]Allow[/]  {escape(verb)}"
        )
        self._paint()
        self.display = True
        self.focus()

    def _paint(self) -> None:
        for i, (_decision, title, key) in enumerate(self._choices):
            on = i == self._index
            radio = "●" if on else "○"
            card = self.query_one(f"#perm-opt-{i}", ChoiceCard)
            card.set_class(on, "-on")
            card.update(f" {radio}  {escape(title)}  [dim]{key}[/]")

    def resolve(self, decision: str) -> None:
        box = self._box
        self._box = None
        self.display = False
        if box is not None:
            box.put(decision)
        try:
            self.app.query_one("#composer", Composer).focus()
        except Exception:
            pass

    def action_move(self, delta: int) -> None:
        if not self._choices:
            return
        self._index = (self._index + delta) % len(self._choices)
        self._paint()

    def action_confirm(self) -> None:
        if self._choices:
            self.resolve(self._choices[self._index][0])

    def action_pick(self, decision: str) -> None:
        self.resolve(decision)

    def on_click(self, event: events.Click) -> None:
        node = event.widget
        while node is not None and node is not self:
            if isinstance(node, ChoiceCard):
                if self._index == node.index:
                    self.action_confirm()
                else:
                    self._index = node.index
                    self._paint()
                event.stop()
                return
            node = node.parent

    def on_key(self, event) -> None:
        if self._box is None:
            return
        if event.key in {"A", "shift+a"}:
            event.stop()
            event.prevent_default()
            self.resolve("always")


class ThoughtBlock(Static):
    """Grok-style collapsed thinking: '▸ Thought for 12.4s'."""

    def __init__(self, seconds: float, body: str) -> None:
        self._seconds = seconds
        self._body = body
        self._expanded = False
        super().__init__(self._collapsed_label(), classes="thought")

    def _collapsed_label(self) -> str:
        return f"[#808080]▸ Thought for {self._seconds:.1f}s[/]"

    def _expanded_label(self) -> str:
        return (
            f"[#808080]▾ Thought for {self._seconds:.1f}s[/]\n"
            f"[#666666]{escape(self._body)}[/]"
        )

    def on_click(self) -> None:
        self._expanded = not self._expanded
        self.update(self._expanded_label() if self._expanded else self._collapsed_label())


class Composer(TextArea):
    BINDINGS = [
        Binding("ctrl+enter", "submit_chat", "send", show=False, priority=True),
        Binding("ctrl+j", "submit_chat", show=False, priority=True),
        Binding("ctrl+v", "paste_smart", show=False, priority=True),
        Binding("alt+v", "paste_smart", show=False, priority=True),
    ]

    class Submitted(Message):
        def __init__(self, display: str, content: str | list) -> None:
            super().__init__()
            self.display = display
            self.content = content

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.draft = Draft()
        self._last_image_at = 0.0

    def action_submit_chat(self) -> None:
        display = self.text
        content = self.draft.expand(display)
        self.post_message(Composer.Submitted(display, content))

    async def _on_key(self, event: events.Key) -> None:
        if self.read_only:
            return
        if event.key in {"enter", "shift+enter", "alt+enter"}:
            event.stop()
            event.prevent_default()
            self.action_submit_chat()
            return
        await super()._on_key(event)

    def action_paste_smart(self) -> None:
        if self._attach_clipboard_image():
            return

    def on_paste(self, event: events.Paste) -> None:
        if self._ingest(event.text or ""):
            event.prevent_default()
            event.stop()

    def reset_draft(self) -> None:
        self.draft = Draft()
        self.clear()

    def _ingest(self, text: str) -> bool:
        if not text.strip():
            return self._attach_clipboard_image()
        paths = image_paths_in_paste(text)
        if paths:
            attached = False
            for path in paths:
                try:
                    data = path.read_bytes()
                except OSError:
                    continue
                if self._add_image(data):
                    attached = True
            return attached
        if len(text) >= LARGE_PASTE:
            chip = self.draft.add_paste(text)
            self.insert(chip + " ")
            return True
        return False

    def _attach_clipboard_image(self) -> bool:
        got = read_clipboard_image()
        if not got:
            return False
        data, mime = got
        return self._add_image(data, mime)

    def _add_image(self, data: bytes, mime: str | None = None) -> bool:
        now = time.monotonic()
        if now - self._last_image_at < 0.3:
            return True
        chip = self.draft.add_image(data, mime)
        if not chip:
            return False
        self._last_image_at = now
        self.insert(chip + " ")
        return True


class Transcript(VerticalScroll):
    can_focus = True

    def on_mount(self) -> None:
        # Pin to the bottom as children grow (Markdown.update is async; a
        # scroll_end right after mount/update still sees the old max_scroll_y).
        self.anchor()

    def follow_end(self) -> None:
        """Re-stick to the bottom after the user jumped away (new turn, /resume)."""
        self.anchor()


class DiffHunk(Vertical):
    """Grok-style edit hunk: line numbers, full-width red/green rows, syntax color."""

    def __init__(self, result: str) -> None:
        super().__init__(classes="diff-hunk")
        self._result = result

    def compose(self) -> ComposeResult:
        parsed = parse_edit_hunk(self._result)
        if parsed is None:
            return
        path, rows = parsed
        lexer = lexer_for(path)
        for op, number, body in rows:
            cls = {"-": "del", "+": "add"}.get(op, "ctx")
            yield Static(render_diff_line(op, number, body, lexer), classes=f"diff-line {cls}")


class HarnessTUI(App[int]):
    ENABLE_COMMAND_PALETTE = False
    TITLE = "harness"
    PALETTE: Theme = PI
    CSS = css_from_theme(PI)

    @property
    def palette(self) -> Theme:
        return type(self).PALETTE

    BINDINGS = [
        Binding("ctrl+d", "quit", "Quit", show=False),
        Binding("ctrl+c", "cancel", "Cancel", show=False),
        Binding("f1", "help", "Help", show=False),
        Binding("escape", "focus_input", "Input", show=False),
    ]

    def __init__(self, runtime: Runtime) -> None:
        super().__init__()
        self.rt = runtime
        self._lock = threading.Lock()
        self._pending: list[tuple[str, str]] = []
        self._stream_kind: str | None = None
        self._stream = ""
        self._live: Static | Markdown | None = None
        self._busy = False
        self._spin_i = 0
        self._tool: Static | None = None
        self._tool_label = ""
        self._reads: list[str] = []
        self._think_started: float | None = None
        self._turn_started: float | None = None
        self._last_seconds: float | None = None
        self._event_gen = 0
        self._accept_events = True

    def compose(self) -> ComposeResult:
        yield Static("", id="chrome")
        yield Transcript(id="log")
        yield PermissionBar()
        yield Composer(
            "",
            id="composer",
            show_line_numbers=False,
            highlight_cursor_line=False,
            soft_wrap=True,
            tab_behavior="focus",
            placeholder="enter send  ·  paste image  ·  esc cancel",
        )
        yield Static("", id="status")

    def on_mount(self) -> None:
        self.rt.loop.on_event = self._queue_event
        self.rt.loop.permissions.ask = self._ask
        self.set_interval(0.04, self._flush)
        self.set_interval(0.08, self._tick)
        self._write_chrome()
        self._welcome()
        self._replay()
        self._refresh_status()
        self.query_one("#composer", Composer).focus()

    def action_help(self) -> None:
        self._notice(self.rt.handle_command("/help").notice)

    def action_focus_input(self) -> None:
        if self._busy:
            self._abort_turn()
            return
        self.query_one("#composer", Composer).focus()

    def action_cancel(self) -> None:
        bar = self.query_one("#permission", PermissionBar)
        if bar._box is not None:
            bar.resolve("deny")
            return
        if self._busy:
            self._abort_turn()
            return
        self.exit(0)

    def _abort_turn(self) -> None:
        self._event_gen += 1
        self._accept_events = False
        self.rt.abort()
        with self._lock:
            self._pending.clear()
        self._flush_live()
        self._finish_tool()
        self._set_busy(False)
        self._notice("cancelled")

    def on_composer_submitted(self, event: Composer.Submitted) -> None:
        display = event.display
        content = event.content
        line = display.strip()
        if self._busy:
            return
        if not line and not has_images(content):
            return
        composer = self.query_one("#composer", Composer)
        composer.reset_draft()
        first = line.split()[0] if line else ""
        if first.startswith("/") and first != "/skill":
            outcome = self.rt.handle_command(line)
            if outcome.switch_ui:
                self.exit(0)
                return
            if outcome.quit:
                self.exit(0)
                return
            if outcome.handled:
                if outcome.notice:
                    self._notice(outcome.notice)
                if first in {"/reset", "/new"}:
                    self._reset_transcript()
                if first == "/resume":
                    self._reset_transcript()
                    self._replay()
                self._refresh_status()
                return
        self._mount_user(display.rstrip() or "[image]")
        self._turn_started = time.monotonic()
        self._think_started = None
        self._event_gen += 1
        gen = self._event_gen
        self._accept_events = True
        self._set_busy(True)
        self.run_worker(
            lambda payload=content, gen=gen: self._worker(payload, gen),
            exclusive=True,
            thread=True,
            name="agent",
        )

    def _worker(self, payload: str | list, gen: int) -> None:
        try:
            result = self.rt.submit(text_of(payload), content=payload)
            reason = result.stopped_reason
        except Exception as exc:
            if gen != self._event_gen:
                return
            self._queue_event("status", f"error: {exc}")
            reason = "error"
        if gen != self._event_gen:
            return
        self._queue_event("_done", reason)

    def _queue_event(self, kind: str, payload: str) -> None:
        if not self._accept_events and kind != "_done":
            return
        with self._lock:
            self._pending.append((kind, payload))

    def _flush(self) -> None:
        with self._lock:
            batch = self._pending
            self._pending = []
        if not batch:
            return
        merged: list[tuple[str, str]] = []
        for kind, payload in batch:
            if merged and kind == merged[-1][0] and kind in {"text_delta", "thinking_delta"}:
                merged[-1] = (kind, merged[-1][1] + payload)
            else:
                merged.append((kind, payload))
        for kind, payload in merged:
            self._apply(kind, payload)

    def _tick(self) -> None:
        if self._busy:
            self._spin_i = (self._spin_i + 1) % len(_SPIN)
            if self._stream_kind == "think" and isinstance(self._live, Static) and self._think_started:
                elapsed = time.monotonic() - self._think_started
                self._live.update(f"[#808080]thinking · {elapsed:.1f}s[/]")
        self._refresh_status()

    def _apply(self, kind: str, payload: str) -> None:
        if kind == "_done":
            self._flush_reads()
            self._flush_live()
            self._finish_tool()
            if self._turn_started:
                self._last_seconds = time.monotonic() - self._turn_started
                self.transcript.mount(
                    Static(f"{self._last_seconds:.1f}s", classes="timing")
                )
            self._set_busy(False)
            if payload == "cancelled":
                self._notice("cancelled")
            return
        if kind == "status":
            self._flush_live()
            self._notice(payload)
            return
        if kind == "thinking_delta":
            self._append_live("think", payload)
            return
        if kind == "text_delta":
            self._flush_reads()
            self._append_live("agent", payload)
            return
        if kind == "assistant_end":
            self._flush_live()
            return
        if kind == "tool_start":
            self._flush_live()
            self._start_tool(payload)
            return
        if kind == "tool_end":
            self._end_tool(payload)

    def _append_live(self, mode: str, payload: str) -> None:
        if self._stream_kind not in {None, mode}:
            self._flush_live()
        if mode == "think" and self._think_started is None:
            self._think_started = time.monotonic()
        self._stream_kind = mode
        self._stream += payload
        if mode == "think":
            elapsed = time.monotonic() - (self._think_started or time.monotonic())
            if self._live is None:
                self._live = Static("", classes="thought")
                self.transcript.mount(self._live)
            self._live.update(f"[#808080]thinking · {elapsed:.1f}s[/]")
            return
        shown = self._stream if len(self._stream) <= _LIVE_CAP else self._stream[-_LIVE_CAP:]
        if not isinstance(self._live, Markdown):
            if self._live is not None:
                self._live.remove()
            md = Markdown(preview_markdown(shown))
            md.add_class("assistant")
            self._live = md
            self.transcript.mount(md)
        else:
            self._live.update(preview_markdown(shown))

    def _flush_live(self) -> None:
        mode = self._stream_kind
        body = self._stream
        widget = self._live
        self._stream_kind = None
        self._stream = ""
        self._live = None
        if mode == "think":
            if widget is not None:
                widget.remove()
            if body.strip() and self._think_started:
                elapsed = time.monotonic() - self._think_started
                self.transcript.mount(ThoughtBlock(elapsed, body))
            self._think_started = None
            return
        if isinstance(widget, Markdown):
            if body.strip():
                widget.update(body)
            else:
                widget.remove()
            return
        if widget is not None:
            widget.remove()
        if body.strip():
            self._mount_assistant(body)

    def _start_tool(self, payload: str) -> None:
        name, arguments = parse_tool_start(payload)
        if name == "read_file":
            self._reads.append(str(arguments.get("path") or ""))
            return
        self._flush_reads()
        label = action_label(name, arguments)
        self._tool_label = label
        t = self.palette
        self._tool = Static(
            f"[{t.muted}]{t.mark}[/]  [bold {t.tool_verb}]{escape(label.split(' ', 1)[0])}[/] [bold]{escape(label.split(' ', 1)[-1] if ' ' in label else '')}[/]",
            classes="action -pending",
        )
        self.transcript.mount(self._tool)

    def _end_tool(self, payload: str) -> None:
        failed = (
            payload.lower().startswith("tool error")
            or payload.lower().startswith("permission denied")
            or "timed out" in payload.lower()
        )
        diff = parse_edit_hunk(payload)
        if self._reads and self._tool is None:
            if failed:
                self._flush_reads()
                t = self.palette
                self.transcript.mount(
                    Static(f"[{t.red}]{t.mark}  Read failed[/]", classes="action -error")
                )
            return
        widget = self._tool
        label = self._tool_label
        self._tool = None
        self._tool_label = ""
        if widget is not None:
            verb, _, detail = label.partition(" ")
            t = self.palette
            color = t.red if failed else t.tool_verb
            mark = "✗" if failed else t.mark
            widget.update(
                f"[{t.muted}]{mark}[/]  [bold {color}]{escape(verb)}[/] [bold]{escape(detail)}[/]"
            )
            widget.set_classes("action -error" if failed else "action")
        if diff and not failed:
            self.transcript.mount(DiffHunk(payload))

    def _flush_reads(self) -> None:
        paths = [p for p in self._reads if p]
        self._reads = []
        if not paths:
            return
        t = self.palette
        if len(paths) == 1:
            body = f"[{t.muted}]{t.mark}[/]  [bold {t.tool_verb}]Read[/] [bold]{escape(paths[0])}[/]"
        else:
            body = f"[{t.muted}]{t.mark}[/]  [bold {t.tool_verb}]Read[/] [bold]{len(paths)} files[/]"
        self.transcript.mount(Static(body, classes="action"))

    def _finish_tool(self) -> None:
        self._flush_reads()
        if self._tool is not None:
            self._tool.set_classes("action")
            self._tool = None
            self._tool_label = ""

    def _mount_user(self, text: str) -> None:
        a = self.palette.accent
        body = f"[bold {a}]you[/bold {a}]\n{escape(text)}"
        self.transcript.mount(Static(body, classes="user"))
        self.transcript.follow_end()

    def _mount_assistant(self, text: str) -> None:
        try:
            widget = Markdown(text)
            widget.add_class("assistant")
            self.transcript.mount(widget)
        except Exception:
            self.transcript.mount(Static(escape(text), classes="assistant"))

    def _notice(self, text: str) -> None:
        if not text:
            return
        self.transcript.mount(Static(escape(text), classes="notice"))
        self.transcript.follow_end()

    def _welcome(self) -> None:
        skills = ", ".join(s.name for s in self.rt.skills) if self.rt.skills else "none"
        a = self.palette.accent
        label = self.palette.name
        body = (
            f"[bold {a}]{label}[/bold {a}]\n"
            f"  {escape(_short_path(self.rt.workspace.root))}\n"
            f"  {escape(self.rt.model_label())}   session {self.rt.session.id}\n"
            f"  skills  {escape(skills)}\n\n"
            "  [dim]/help  /model  /resume  /tui   enter send   esc cancel[/dim]"
        )
        self.transcript.mount(Static(body, classes="welcome"))

    def _replay(self) -> None:
        for message in self.rt.session.messages:
            if message.role is Role.USER:
                self._mount_user(text_of(message.content))
            elif message.role is Role.ASSISTANT:
                if message.content:
                    self._mount_assistant(message.content)
                if message.tool_calls:
                    names = ", ".join(action_label(c.name, c.arguments) for c in message.tool_calls)
                    t = self.palette
                    self.transcript.mount(
                        Static(
                            f"[{t.muted}]{t.mark}[/]  [bold {t.tool_verb}]{escape(names)}[/]",
                            classes="action",
                        )
                    )
            elif message.role is Role.TOOL:
                if parse_edit_hunk(message.content):
                    self.transcript.mount(DiffHunk(message.content))
        self.transcript.follow_end()

    def _reset_transcript(self) -> None:
        self.transcript.remove_children()
        self._live = None
        self._tool = None
        self._tool_label = ""
        self._reads = []
        self._stream_kind = None
        self._stream = ""
        self._think_started = None
        self._welcome()
        self.transcript.follow_end()

    def _set_busy(self, busy: bool) -> None:
        self._busy = busy
        composer = self.query_one("#composer", Composer)
        composer.disabled = busy
        composer.placeholder = (
            "working…  esc/ctrl+c cancel" if busy else "enter send  ·  paste image  ·  esc cancel"
        )
        if not busy:
            composer.focus()

    def _write_chrome(self) -> None:
        t = self.palette
        self.query_one("#chrome", Static).update(
            f"[bold {t.accent}]{t.mark}[/bold {t.accent}]  {t.name}"
            f"                                  [dim]{escape(self.rt.session.id)}[/dim]"
        )

    def _refresh_status(self) -> None:
        s = self.rt.session
        spin = f"{_SPIN[self._spin_i]}  " if self._busy else "   "
        cost = f"  ·  ${s.cost_usd:.4f}" if s.cost_usd else ""
        cwd = _short_path(self.rt.workspace.root)
        if len(cwd) > 36:
            cwd = "…" + cwd[-35:]
        line = (
            f"{spin}[bold {self.palette.accent}]{escape(self.rt.model_label())}[/]  ·  "
            f"↑{_fmt_n(s.prompt_tokens)} ↓{_fmt_n(s.completion_tokens)}{cost}  ·  "
            f"[dim]{escape(cwd)}[/dim]"
        )
        self.query_one("#status", Static).update(line)

    def _ask(self, call: ToolCall) -> bool | str:
        box: queue.Queue[bool | str] = queue.Queue()
        self.call_from_thread(self._show_permission, call, box)
        while True:
            try:
                return box.get(timeout=0.2)
            except queue.Empty:
                if self.rt.cancel.is_set():
                    return False

    def _show_permission(self, call: ToolCall, box: queue.Queue[bool | str]) -> None:
        self.query_one("#permission", PermissionBar).present(call, box)

    @property
    def transcript(self) -> Transcript:
        return self.query_one("#log", Transcript)


def run_tui(runtime: Runtime) -> int:
    os.environ.setdefault("TERM", os.environ.get("TERM", "xterm-256color"))
    return HarnessTUI(runtime).run() or 0
