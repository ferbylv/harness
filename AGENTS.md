# Harness

Small coding-agent loop. Read `README.md` for the map and `STATUS.md` for done / not-done / how to add it.

## Layout

- `src/harness/app.py` — CLI; picks a UserInterface by name
- `src/harness/ui/` — front-end protocol + registry (`textual`, `repl`, plugins); spec in `ui/SPEC.md`; `/tui` switches
- `src/harness/runtime.py` — session, slash commands, submit()
- `src/harness/tui.py` — Textual implementation; listens to on_event only
- `src/harness/loop.py` — model ↔ tools until stop; rebuilds system prompt each complete
- `src/harness/store.py` — `.harness/sessions/<id>.json`
- `src/harness/context.py` — `AGENTS.md` / `CLAUDE.md` + skills into system prompt
- `src/harness/skills.py` — `SKILL.md` discovery and match
- `src/harness/compact.py` — token-budget compact, snap to user turns
- `src/harness/tools/` — one file per tool, register in `tools/__init__.py`
- `src/harness/llm/` — `complete(messages, tools, on_delta=None)`
- `src/harness/prompts/system.md` — identity

## Conventions

- Tools return strings. Never raise into the model loop; `AgentLoop._run_tool` already catches.
- Mutating tools set `ToolSpec.mutating = True`.
- Paths go through `Workspace.resolve`. Do not open user paths raw.
- Session transcript does not store the system prompt; it is rebuilt from files + matched skills.
- Compact before `complete` when `last_prompt_tokens >= HARNESS_COMPACT_AT`.
