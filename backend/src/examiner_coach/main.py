import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from examiner_coach.config import settings


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    Routes are imported inside the factory so app construction stays testable
    and importing this module does not eagerly pull every route dependency.
    """
    app = FastAPI(
        title="Examiner Coach",
        description="AI-powered OSCE examiner feedback training tool",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logging.basicConfig(level=settings.log_level.upper())

    # Register active API route groups.
    from examiner_coach.api.routes import health
    app.include_router(health.router, prefix="/api", tags=["health"])

    from examiner_coach.api.routes import audio
    app.include_router(audio.router, prefix="/api", tags=["audio"])

    from examiner_coach.api.routes import evaluation
    app.include_router(evaluation.router, prefix="/api", tags=["evaluation"])

    from examiner_coach.api.routes import coaching
    app.include_router(coaching.router, prefix="/api", tags=["coaching"])

    return app


app = create_app()
