from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

PROVIDERS = {
    "xai": {
        "base_url": "https://api.x.ai/v1",
        "api_key_env": "XAI_API_KEY",
        "model": "grok-4-fast-non-reasoning",
    },
    "openai": {
        "base_url": "https://api.openai.com/v1",
        "api_key_env": "OPENAI_API_KEY",
        "model": "gpt-4.1",
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_env": "OPENROUTER_API_KEY",
        "model": "openai/gpt-4.1-mini",
    },
}

# Unknown providers are treated as OpenAI-compatible, not as xAI.
_OPENAI_COMPAT = {
    "base_url": "https://api.openai.com/v1",
    "api_key_env": "OPENAI_API_KEY",
    "model": "gpt-4.1",
}

# After the provider-specific var, accept any of these so a custom
# HARNESS_PROVIDER=openrouter + OPENAI_API_KEY setup still works.
_KEY_FALLBACKS = (
    "HARNESS_API_KEY",
    "OPENROUTER_API_KEY",
    "OPENAI_API_KEY",
    "XAI_API_KEY",
)


@dataclass(frozen=True)
class Config:
    workspace: Path
    provider: str
    model: str
    base_url: str
    api_key: str
    mock: bool
    yolo: bool
    stream: bool
    max_turns: int
    max_tool_output: int
    compact_at: int
    keep_last: int
    compact_summarize: bool
    reasoning: bool


def load_config(workspace: Path | None = None) -> Config:
    _load_dotenv()
    provider = os.getenv("HARNESS_PROVIDER", "xai").lower().strip()
    defaults = PROVIDERS.get(provider, _OPENAI_COMPAT)
    mock = _truthy(os.getenv("HARNESS_MOCK"))
    api_key, _source = resolve_api_key(defaults["api_key_env"])
    return Config(
        workspace=(workspace or Path.cwd()).resolve(),
        provider=provider,
        model=os.getenv("HARNESS_MODEL", defaults["model"]),
        base_url=os.getenv("HARNESS_BASE_URL", defaults["base_url"]).rstrip("/"),
        api_key=api_key,
        mock=mock,
        yolo=_truthy(os.getenv("HARNESS_YOLO")),
        stream=_env_bool("HARNESS_STREAM", default=True),
        max_turns=int(os.getenv("HARNESS_MAX_TURNS", "30")),
        max_tool_output=int(os.getenv("HARNESS_MAX_TOOL_OUTPUT", "80_000")),
        compact_at=int(os.getenv("HARNESS_COMPACT_AT", "32000")),
        keep_last=int(os.getenv("HARNESS_KEEP_LAST", "16")),
        compact_summarize=_env_bool("HARNESS_COMPACT_SUMMARIZE", default=not mock),
        reasoning=_env_bool("HARNESS_REASONING", default=True),
    )


def resolve_api_key(primary: str) -> tuple[str, str | None]:
    seen: list[str] = []
    for name in (primary, *_KEY_FALLBACKS):
        if name in seen:
            continue
        seen.append(name)
        value = (os.getenv(name) or "").strip()
        if value:
            return value, name
    return "", None


def missing_key_hint(provider: str) -> str:
    defaults = PROVIDERS.get(provider, _OPENAI_COMPAT)
    names = []
    for name in (defaults["api_key_env"], *_KEY_FALLBACKS):
        if name not in names:
            names.append(name)
    return (
        f"missing API key for provider {provider!r}. "
        f"set one of: {', '.join(names)}. "
        "unknown HARNESS_PROVIDER values are OpenAI-compatible and read OPENAI_API_KEY."
    )


def _load_dotenv() -> None:
    # Explicit path: bare load_dotenv() walks from this source file and would
    # pick a repo .env even when tests chdir into a temp directory.
    folder = Path.cwd()
    for _ in range(8):
        candidate = folder / ".env"
        if candidate.is_file():
            load_dotenv(candidate)
            return
        if (folder / ".git").exists() or folder.parent == folder:
            return
        folder = folder.parent


def _env_bool(name: str, *, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return _truthy(raw)


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "on"}
