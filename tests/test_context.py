from harness.context import build_system_prompt, load_agents_md
from harness.skills import discover_skills, match_skills
from harness.workspace import Workspace


def test_agents_md_is_folded_into_system_prompt(tmp_path):
    (tmp_path / "AGENTS.md").write_text("Always use type hints.", encoding="utf-8")
    ws = Workspace(tmp_path)
    text = build_system_prompt(ws)
    assert "Always use type hints." in text
    assert str(tmp_path / "AGENTS.md") in load_agents_md(ws)


def test_claude_md_used_when_agents_missing(tmp_path):
    (tmp_path / "CLAUDE.md").write_text("Prefer tests.", encoding="utf-8")
    assert "Prefer tests." in load_agents_md(Workspace(tmp_path))


def test_skill_discovery_and_match(tmp_path):
    skill_dir = tmp_path / ".harness" / "skills" / "review"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        "---\nname: review\ndescription: Review a pull request for bugs\n---\nLook at the diff.\n",
        encoding="utf-8",
    )
    ws = Workspace(tmp_path)
    skills = [s for s in discover_skills(ws) if str(tmp_path) in str(s.path)]
    assert [s.name for s in skills] == ["review"]
    matched = match_skills("please review this pull request", skills)
    assert matched and matched[0].name == "review"
    assert not match_skills("what is the weather", skills)
    explicit = match_skills("/skill review", skills)
    assert explicit[0].body == "Look at the diff."
    prompt = build_system_prompt(ws, skills=skills, injected=matched)
    assert "Look at the diff." in prompt
    assert "review:" in prompt
