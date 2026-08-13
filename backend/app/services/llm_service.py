from langchain_openai import ChatOpenAI
from langchain_core.language_models import BaseChatModel
from app.config.settings import settings
import logging

logger = logging.getLogger(__name__)

# Runtime provider override — changed via the secret toggle API without restarting
_runtime_provider: str | None = None


def get_active_provider() -> str:
    return _runtime_provider or settings.LLM_PROVIDER.lower()


def set_provider(provider: str) -> str:
    global _runtime_provider
    _runtime_provider = provider.lower()
    logger.info(f"LLM provider switched to: {_runtime_provider}")
    return _runtime_provider


def get_llm(temperature: float = 0.1, streaming: bool = False) -> BaseChatModel:
    provider = get_active_provider()

    if provider == "openrouter":
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=temperature,
            streaming=streaming,
            api_key=settings.OPENROUTER_API_KEY or "no-key",
            base_url="https://openrouter.ai/api/v1",
            max_retries=3,
            default_headers={
                "HTTP-Referer": "https://agent-orchestration.app",
                "X-Title": "Agent Orchestration System",
            },
        )

    if provider == "groq":
        return ChatOpenAI(
            model=settings.GROQ_MODEL,
            temperature=temperature,
            streaming=streaming,
            api_key=settings.GROQ_API_KEY or "no-key",
            base_url="https://api.groq.com/openai/v1",
            max_retries=3,
        )

    if provider == "ollama":
        try:
            from langchain_community.chat_models import ChatOllama
            return ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=temperature,
            )
        except ImportError:
            logger.warning("Ollama not available, falling back to OpenRouter")
            return get_llm.__wrapped__(temperature=temperature, streaming=streaming)

    if provider == "openai":
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            temperature=temperature,
            streaming=streaming,
            max_retries=3,
        )

    raise ValueError(f"Unknown provider: {provider}")
