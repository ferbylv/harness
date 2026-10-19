import os
from pathlib import Path

from harness.config import load_config, resolve_api_key


def test_openrouter_accepts_openai_api_key(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_PROVIDER", "openrouter")
    monkeypatch.setenv("HARNESS_MODEL", "qwen/qwen3.8-27b:free")
    monkeypatch.setenv("HARNESS_BASE_URL", "https://openrouter.ai/api/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-or-test")
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("HARNESS_API_KEY", raising=False)
    monkeypatch.delenv("HARNESS_MOCK", raising=False)
    cfg = load_config(tmp_path)
    assert cfg.provider == "openrouter"
    assert cfg.api_key == "sk-or-test"
    assert cfg.base_url == "https://openrouter.ai/api/v1"
    assert cfg.model == "qwen/qwen3.8-27b:free"


def test_unknown_provider_does_not_require_xai_key(monkeypatch, tmp_path):
    monkeypatch.setenv("HARNESS_PROVIDER", "my-proxy")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-proxy")
    monkeypatch.setenv("HARNESS_BASE_URL", "https://example.com/v1")
    monkeypatch.delenv("XAI_API_KEY", raising=False)
    monkeypatch.delenv("HARNESS_API_KEY", raising=False)
    monkeypatch.delenv("HARNESS_MOCK", raising=False)
    cfg = load_config(tmp_path)
    assert cfg.api_key == "sk-proxy"
    assert cfg.base_url == "https://example.com/v1"


def test_resolve_prefers_provider_specific(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "or-key")
    monkeypatch.setenv("OPENAI_API_KEY", "oa-key")
    value, source = resolve_api_key("OPENROUTER_API_KEY")
    assert value == "or-key"
    assert source == "OPENROUTER_API_KEY"


def test_dotenv_is_read_from_file(monkeypatch, tmp_path):
    env_file = tmp_path / ".env"
    env_file.write_text("HARNESS_PROVIDER=openrouter\nOPENAI_API_KEY=from-file\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    for name in (
        "HARNESS_PROVIDER",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "XAI_API_KEY",
        "HARNESS_API_KEY",
        "HARNESS_MOCK",
        "HARNESS_MODEL",
        "HARNESS_BASE_URL",
    ):
        monkeypatch.delenv(name, raising=False)
    cfg = load_config(Path(tmp_path))
    assert cfg.provider == "openrouter"
    assert cfg.api_key == "from-file"
