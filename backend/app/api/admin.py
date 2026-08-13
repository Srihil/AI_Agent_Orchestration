from fastapi import APIRouter
from app.services.llm_service import get_active_provider, set_provider
from app.config.settings import settings

router = APIRouter(prefix="/admin", tags=["admin"])

PROVIDER_CONFIGS = {
    "openrouter": {
        "provider": "openrouter",
        "model": settings.LLM_MODEL,
        "label": "OpenRouter",
        "model_label": settings.LLM_MODEL,
    },
    "groq": {
        "provider": "groq",
        "model": settings.GROQ_MODEL,
        "label": "Groq",
        "model_label": settings.GROQ_MODEL,
    },
}


@router.get("/provider")
async def get_provider():
    active = get_active_provider()
    config = PROVIDER_CONFIGS.get(active, PROVIDER_CONFIGS["openrouter"])
    return {"active": active, **config}


@router.post("/provider/toggle")
async def toggle_provider():
    current = get_active_provider()
    next_provider = "groq" if current == "openrouter" else "openrouter"
    set_provider(next_provider)
    config = PROVIDER_CONFIGS.get(next_provider, PROVIDER_CONFIGS["openrouter"])
    return {"active": next_provider, "switched_from": current, **config}
