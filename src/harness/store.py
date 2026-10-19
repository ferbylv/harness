from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from harness.session import Session
from harness.workspace import Workspace


@dataclass(frozen=True)
class SessionInfo:
    id: str
    updated_at: str
    model: str
    messages: int
    path: Path


class SessionStore:
    def __init__(self, workspace: Workspace) -> None:
        self.dir = workspace.root / ".harness" / "sessions"

    def path_for(self, session_id: str) -> Path:
        return self.dir / f"{session_id}.json"

    def save(self, session: Session) -> Path:
        path = self.path_for(session.id)
        session.save(path)
        latest = self.dir / "latest"
        latest.write_text(session.id, encoding="utf-8")
        return path

    def load(self, session_id: str) -> Session:
        path = self.path_for(session_id)
        if not path.is_file():
            raise FileNotFoundError(f"no session {session_id}")
        return Session.load(path)

    def latest_id(self) -> str | None:
        pointer = self.dir / "latest"
        if pointer.is_file():
            sid = pointer.read_text(encoding="utf-8").strip()
            if sid and self.path_for(sid).is_file():
                return sid
        infos = self.list()
        return infos[0].id if infos else None

    def latest(self) -> Session | None:
        sid = self.latest_id()
        return self.load(sid) if sid else None

    def list(self) -> list[SessionInfo]:
        if not self.dir.is_dir():
            return []
        infos: list[SessionInfo] = []
        for path in self.dir.glob("*.json"):
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            infos.append(
                SessionInfo(
                    id=str(data.get("id") or path.stem),
                    updated_at=str(data.get("updated_at") or ""),
                    model=str(data.get("model") or ""),
                    messages=len(data.get("messages") or []),
                    path=path,
                )
            )
        infos.sort(key=lambda item: item.updated_at, reverse=True)
        return infos
