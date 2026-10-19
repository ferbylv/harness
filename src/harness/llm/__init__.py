import os

from harness.cancel import CancelToken
from harness.config import Config, missing_key_hint
from harness.llm.base import LLMClient
from harness.llm.mock import MockClient
from harness.llm.openai_compat import OpenAICompatClient


def build_llm(config: Config, cancel: CancelToken | None = None) -> LLMClient:
    if config.mock:
        return MockClient(cancel=cancel)
    if not config.api_key:
        raise RuntimeError(missing_key_hint(config.provider))
    return OpenAICompatClient(
        base_url=config.base_url,
        api_key=config.api_key,
        model=config.model,
        stream=config.stream,
        include_reasoning=config.reasoning,
        cancel=cancel,
        max_retries=int(os.getenv("HARNESS_RETRY", "3")),
    )


__all__ = ["LLMClient", "MockClient", "OpenAICompatClient", "build_llm"]
