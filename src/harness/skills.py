from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from harness.workspace import Workspace

_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?(.*)\Z", re.DOTALL)


@dataclass(frozen=True)
class Skill:
    name: str
    description: str
    body: str
    path: Path


def discover_skills(workspace: Workspace) -> list[Skill]:
    roots = [
        Path.home() / ".harness" / "skills",
        workspace.root / ".harness" / "skills",
        workspace.root / "skills",
    ]
    found: dict[str, Skill] = {}
    for root in roots:
        if not root.is_dir():
            continue
        for skill_md in sorted(root.glob("*/SKILL.md")):
            skill = _parse_skill(skill_md)
            if skill:
                found[skill.name] = skill
    return list(found.values())


def match_skills(query: str, skills: list[Skill], *, limit: int = 3) -> list[Skill]:
    text = query.strip()
    if not text or not skills:
        return []
    explicit = _explicit_names(text)
    if explicit:
        by_name = {s.name.lower(): s for s in skills}
        return [by_name[n] for n in explicit if n in by_name][:limit]
    scored: list[tuple[int, Skill]] = []
    hay = text.lower()
    for skill in skills:
        score = _score(hay, skill)
        if score > 0:
            scored.append((score, skill))
    scored.sort(key=lambda item: (-item[0], item[1].name))
    return [skill for _, skill in scored[:limit]]


def catalog_text(skills: list[Skill]) -> str:
    if not skills:
        return ""
    lines = ["Available skills (loaded when the user task matches the description):"]
    for skill in skills:
        lines.append(f"- {skill.name}: {skill.description}")
    return "\n".join(lines)


def _explicit_names(text: str) -> list[str]:
    names: list[str] = []
    for match in re.finditer(r"/skill(?:s)?[:\s]+([a-z0-9][a-z0-9_-]*)", text.lower()):
        names.append(match.group(1))
    return names


def _score(hay: str, skill: Skill) -> int:
    score = 0
    name = skill.name.lower()
    if name and name in hay:
        score += 8
    needle = skill.description.lower()
    if needle and needle in hay:
        score += 10
    words = {w for w in re.findall(r"[a-z0-9]{4,}", needle) if w not in _STOP}
    hits = sum(1 for w in words if w in hay)
    if hits:
        score += hits
    return score


def _parse_skill(path: Path) -> Skill | None:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError:
        return None
    match = _FRONTMATTER.match(raw)
    meta: dict[str, str] = {}
    body = raw.strip()
    if match:
        meta = _parse_fields(match.group(1))
        body = match.group(2).strip()
    name = (meta.get("name") or path.parent.name).strip()
    description = (meta.get("description") or "").strip()
    if not name:
        return None
    return Skill(name=name, description=description or name, body=body, path=path)


def _parse_fields(block: str) -> dict[str, str]:
    fields: dict[str, str] = {}
    for line in block.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        fields[key.strip().lower()] = value.strip().strip("\"'")
    return fields


_STOP = {
    "with",
    "from",
    "this",
    "that",
    "when",
    "your",
    "into",
    "using",
    "about",
    "for",
    "and",
    "the",
}
