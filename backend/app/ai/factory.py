from app.ai.gemini import GeminiProvider
from app.ai.mock import MockLLMProvider
from app.ai.provider import LLMProvider
from app.config import Settings


def build_llm_provider(settings: Settings) -> LLMProvider:
    if settings.real_gemini_enabled:
        return GeminiProvider(settings)
    return MockLLMProvider()
