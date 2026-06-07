import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from examiner_coach.config import settings


def create_app() -> FastAPI:
    """
    Application factory — creates and configures the FastAPI instance.
    Import routes here to keep main.py clean and testable.
    """

    app = FastAPI(
        title="Examiner Coach",
        description="AI-powered OSCE examiner feedback training tool",
        version="0.1.0",
        docs_url="/docs" if settings.is_development else None,
        redoc_url="/redoc" if settings.is_development else None,
    )

    # ── CORS ─────────────────────────────────────────────────
    # In development: allow all origins (frontend dev server)
    # In production: restrict to actual deployment domain
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"] if settings.is_development else ["https://your-domain.de"], # Add your production domain here
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Logging ──────────────────────────────────────────────
    logging.basicConfig(level=settings.log_level.upper())

    # ── Routes ───────────────────────────────────────────────
    from examiner_coach.api.routes import health
    app.include_router(health.router, prefix="/api", tags=["health"])

    # These will be uncommented as we build each service:
    from examiner_coach.api.routes import audio
    app.include_router(audio.router, prefix="/api", tags=["audio"])

    from examiner_coach.api.routes import evaluation
    app.include_router(evaluation.router, prefix="/api", tags=["evaluation"])

    from examiner_coach.api.routes import coaching
    app.include_router(coaching.router, prefix="/api", tags=["coaching"])

    return app


app = create_app()
