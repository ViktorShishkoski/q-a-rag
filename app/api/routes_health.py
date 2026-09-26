from __future__ import annotations

from fastapi import APIRouter, Depends

from app.core.dependencies import ServiceContainer, get_services
from app.core.errors import RagError
from app.models.responses import HealthResponse, OllamaHealth

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponse)
def health(services: ServiceContainer = Depends(get_services)) -> HealthResponse:
    reachable = services.generation_provider.health_check()
    model_available = False
    if reachable:
        try:
            model_available = services.generation_provider.is_model_available(
                services.settings.ollama_generation_model
            )
        except RagError:
            model_available = False

    try:
        services.vector_store.count()
        qdrant_ok = True
    except Exception:
        qdrant_ok = False

    status = "ok" if (reachable and model_available and qdrant_ok) else "degraded"
    return HealthResponse(
        status=status,
        ollama=OllamaHealth(reachable=reachable, model_available=model_available),
        qdrant=qdrant_ok,
    )
