from __future__ import annotations

from pathlib import Path

from harness.skills import Skill, catalog_text
from harness.workspace import Workspace

_PROMPT_FILE = Path(__file__).parent / "prompts" / "system.md"
_CONTEXT_NAMES = ("AGENTS.md", "CLAUDE.md")


def build_system_prompt(
    workspace: Workspace,
    *,
    skills: list[Skill] | None = None,
    injected: list[Skill] | None = None,
) -> str:
    text = _PROMPT_FILE.read_text(encoding="utf-8").format(workspace=workspace.root)
    agents = load_agents_md(workspace)
    if agents:
        text += "\n\n# Project instructions\n" + agents
    catalog = catalog_text(skills or [])
    if catalog:
        text += "\n\n# Skills\n" + catalog
    for skill in injected or []:
        text += f"\n\n# Skill: {skill.name}\n{skill.body}"
    return text


def load_agents_md(workspace: Workspace) -> str:
    chunks: list[str] = []
    seen: set[Path] = set()
    global_path = Path.home() / ".harness" / "AGENTS.md"
    _append(chunks, seen, global_path)
    for folder in _walk_up(workspace.root):
        chosen = _pick_context_file(folder)
        if chosen:
            _append(chunks, seen, chosen)
        if (folder / ".git").exists():
            break
    return "\n\n".join(chunks)


def _pick_context_file(folder: Path) -> Path | None:
    for name in _CONTEXT_NAMES:
        path = folder / name
        if path.is_file():
            return path
    return None


def _walk_up(start: Path) -> list[Path]:
    folder = start.resolve()
    chain = [folder]
    for _ in range(8):
        if folder.parent == folder:
            break
        folder = folder.parent
        chain.append(folder)
    chain.reverse()
    return chain


def _append(chunks: list[str], seen: set[Path], path: Path) -> None:
    try:
        resolved = path.resolve()
    except OSError:
        return
    if resolved in seen or not path.is_file():
        return
    seen.add(resolved)
    try:
        body = path.read_text(encoding="utf-8").strip()
    except OSError:
        return
    if not body:
        return
    chunks.append(f"## {path}\n{body}")
