from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass

from harness.cancel import CancelToken
from harness.config import Config, load_config
from harness.content import Content, text_of
from harness.context import build_system_prompt
from harness.llm import build_llm
from harness.loop import AgentLoop, LoopResult
from harness.permissions import AskFn, PermissionGate
from harness.session import Session
from harness.skills import Skill, discover_skills, match_skills
from harness.store import SessionStore
from harness.tools import default_tools
from harness.workspace import Workspace

EventHandler = Callable[[str, str], None]

HELP = """
  /help          this text
  /reset /new    new session (old one stays on disk)
  /sessions      list saved sessions
  /resume [id]   load a session (latest if omitted)
  /model [name]  show or switch the model
  /cost          tokens and cost for this session
  /compact       force context compaction
  /skills        list discovered skills
  /tui [name]    list or switch front-end (textual, repl, plugins)
  /quit          exit

  TUI: enter send  ·  esc/ctrl+c cancel
""".strip()


@dataclass
class CommandResult:
    handled: bool
    quit: bool = False
    notice: str = ""
    switch_ui: str | None = None


class Runtime:
    def __init__(
        self,
        *,
        config: Config,
        persist: bool = True,
        ask: AskFn | None = None,
        on_event: EventHandler | None = None,
        session: Session | None = None,
    ) -> None:
        self.config = config
        self.workspace = Workspace(config.workspace)
        self.store = SessionStore(self.workspace)
        self.skills = discover_skills(self.workspace)
        self.persist_enabled = persist
        self.switch_ui: str | None = None
        self.cancel = CancelToken()
        self.llm = build_llm(config, cancel=self.cancel)
        self.session = session or Session.start(self.workspace, model=config.model)
        tools = default_tools(self.workspace, config, cancel=self.cancel)
        self.loop = AgentLoop(
            llm=self.llm,
            tools=tools,
            session=self.session,
            permissions=PermissionGate(tools=tools, yolo=config.yolo, ask=ask),
            max_turns=config.max_turns,
            on_event=on_event,
            build_system=self._build_system,
            compact_at=config.compact_at,
            keep_last=config.keep_last,
            compact_summarize=config.compact_summarize,
            cancel=self.cancel,
        )

    @classmethod
    def from_args(cls, args: argparse.Namespace, *, ask: AskFn | None = None, on_event: EventHandler | None = None) -> Runtime:
        workspace = _workspace_from_args(args)
        config = load_config(workspace)
        store = SessionStore(Workspace(config.workspace))
        persist = not args.no_session
        session = _open_session(store, config, args)
        return cls(config=config, persist=persist, ask=ask, on_event=on_event, session=session)

    def persist(self) -> None:
        if self.persist_enabled:
            self.store.save(self.session)

    def model_name(self) -> str:
        return self.session.model or getattr(self.llm, "model", None) or self.config.model

    def model_label(self) -> str:
        if self.config.mock:
            return "mock"
        return f"{self.config.provider}:{self.model_name()}"

    def status_line(self) -> str:
        s = self.session
        cost = f"  ${s.cost_usd:.4f}" if s.cost_usd else ""
        return (
            f"{self.model_label()}  session {s.id}  "
            f"↑{s.prompt_tokens} ↓{s.completion_tokens}{cost}  {self.workspace.root}"
        )

    def abort(self) -> None:
        self.cancel.cancel()

    def submit(self, text: str, *, content: Content | None = None) -> LoopResult:
        self.cancel.reset()
        payload = text if content is None else content
        injected = match_skills(text_of(payload), self.skills)
        result = self.loop.run(text_of(payload), injected=injected, content=payload)
        self.persist()
        return result

    def handle_command(self, line: str) -> CommandResult:
        if not line.startswith("/"):
            return CommandResult(handled=False)
        cmd, _, rest = line.partition(" ")
        rest = rest.strip()
        if cmd == "/skill":
            return CommandResult(handled=False)
        if cmd in {"/q", "/quit", "/exit"}:
            self.switch_ui = None
            self.persist()
            return CommandResult(handled=True, quit=True)
        if cmd in {"/tui", "/ui"}:
            from harness.ui import get, load_builtins, names

            load_builtins()
            if not rest:
                listed = ", ".join(names()) or "(none)"
                return CommandResult(handled=True, notice=f"uis: {listed}\n/tui <name> to switch")
            key = rest.lower()
            try:
                get(key)
            except KeyError as exc:
                return CommandResult(handled=True, notice=str(exc))
            self.switch_ui = key
            self.persist()
            return CommandResult(
                handled=True,
                switch_ui=key,
                notice=f"switching to {key}",
            )
        if cmd == "/help":
            return CommandResult(handled=True, notice=HELP)
        if cmd in {"/reset", "/new"}:
            self.session.reset(self.workspace, model=self.model_name())
            self.persist()
            return CommandResult(handled=True, notice=f"new session {self.session.id}")
        if cmd == "/sessions":
            infos = self.store.list()
            if not infos:
                return CommandResult(handled=True, notice="no saved sessions")
            lines = []
            for info in infos[:20]:
                mark = "*" if info.id == self.session.id else " "
                lines.append(f"{mark} {info.id}  {info.updated_at}  {info.messages} msgs  {info.model}")
            return CommandResult(handled=True, notice="\n".join(lines))
        if cmd == "/resume":
            sid = rest or self.store.latest_id()
            if not sid:
                return CommandResult(handled=True, notice="no session to resume")
            loaded = self.store.load(sid)
            self._copy_session(loaded)
            return CommandResult(
                handled=True,
                notice=f"resumed {self.session.id}, {len(self.session.messages)} messages",
            )
        if cmd == "/model":
            if not rest:
                return CommandResult(handled=True, notice=self.model_name())
            if hasattr(self.llm, "model"):
                self.llm.model = rest
            self.session.model = rest
            return CommandResult(handled=True, notice=f"model {rest}")
        if cmd in {"/cost", "/session"}:
            s = self.session
            return CommandResult(
                handled=True,
                notice=(
                    f"id {s.id}  model {s.model or self.model_name()}\n"
                    f"tokens ↑{s.prompt_tokens} ↓{s.completion_tokens}  "
                    f"last prompt {s.last_prompt_tokens}  cost ${s.cost_usd:.6f}"
                ),
            )
        if cmd == "/compact":
            if self.loop.compact_now():
                self.persist()
                return CommandResult(handled=True, notice="compacted")
            return CommandResult(handled=True, notice="nothing to compact")
        if cmd == "/skills":
            if not self.skills:
                return CommandResult(
                    handled=True,
                    notice="no skills found. put SKILL.md under .harness/skills/<name>/",
                )
            body = "\n".join(f"- {s.name}: {s.description}" for s in self.skills)
            return CommandResult(handled=True, notice=body)
        return CommandResult(handled=True, notice=f"unknown command {cmd}. /help")

    def _build_system(self, user_text: str, injected: list[Skill]) -> str:
        return build_system_prompt(self.workspace, skills=self.skills, injected=injected)

    def _copy_session(self, loaded: Session) -> None:
        self.session.id = loaded.id
        self.session.messages = loaded.messages
        self.session.model = loaded.model
        self.session.created_at = loaded.created_at
        self.session.updated_at = loaded.updated_at
        self.session.prompt_tokens = loaded.prompt_tokens
        self.session.completion_tokens = loaded.completion_tokens
        self.session.cost_usd = loaded.cost_usd
        self.session.last_prompt_tokens = loaded.last_prompt_tokens


def _open_session(store: SessionStore, config: Config, args: argparse.Namespace) -> Session:
    workspace = Workspace(config.workspace)
    if args.no_session:
        return Session.start(workspace, model=config.model)
    if args.resume:
        session = store.load(args.resume)
        session.model = session.model or config.model
        return session
    if args.continue_session:
        session = store.latest()
        if session is None:
            return Session.start(workspace, model=config.model)
        session.model = session.model or config.model
        return session
    return Session.start(workspace, model=config.model)


def _workspace_from_args(args: argparse.Namespace):
    from pathlib import Path

    return Path(args.workspace).resolve() if args.workspace else None
