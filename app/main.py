"""FastAPI app assembly.

create_app() accepts an optional container_factory so callers (tests, or a
future UI process) can supply a pre-built ServiceContainer instead of the
production one built from environment settings - this keeps the default
`app` import side-effect-free-ish (lazy providers, no eager model loads) while
still letting tests fully swap in mock/tmp-path-backed services without
touching real project data directories.
"""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes_analysis import router as analysis_router
from app.api.routes_documents import router as documents_router
from app.api.routes_health import router as health_router
from app.api.routes_query import router as query_router
from app.core.dependencies import ServiceContainer, build_services, get_settings
from app.core.errors import RagError, status_code_for
from app.core.logging import configure_logging

ContainerFactory = Callable[[], ServiceContainer]

_DATA_DIRS = ("data/raw", "data/processed", "data/indexes", "data/evaluation")


def create_app(container_factory: ContainerFactory | None = None) -> FastAPI:
    factory = container_factory or (lambda: build_services(get_settings()))

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        settings = get_settings()
        configure_logging(settings.log_level)
        for d in _DATA_DIRS:
            Path(d).mkdir(parents=True, exist_ok=True)
        app.state.services = factory()
        yield

    app = FastAPI(title="Q&A RAG Backend", version="0.1.0", lifespan=lifespan)

    app.include_router(health_router)
    app.include_router(documents_router)
    app.include_router(query_router)
    app.include_router(analysis_router)

    @app.exception_handler(RagError)
    async def rag_error_handler(request: Request, exc: RagError) -> JSONResponse:
        return JSONResponse(
            status_code=status_code_for(exc),
            content={"error": str(exc), "type": type(exc).__name__},
        )

    # Mounted last so it's a fallback: the routers above already claim
    # /health, /documents*, /query and take precedence over this catch-all.
    frontend_dist = Path("frontend/dist")
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")

    return app


app = create_app()
