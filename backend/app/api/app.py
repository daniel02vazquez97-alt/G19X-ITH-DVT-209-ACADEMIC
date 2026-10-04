"""FastAPI application of the API V1 (`docs/07` §7, `DT-064` to `DT-067`)."""

from __future__ import annotations

from fastapi import FastAPI

from . import __version__, correlation, errors
from .auth import DevTokenValidator, TokenValidator
from .routers import forecasts, health, inventory, me, products, recommendations, runs
from .settings import Settings, load_settings

TITLE = "Motor Predictivo de Abastecimiento — API V1 (solo lectura)"


def create_app(settings: Settings | None = None, validator: TokenValidator | None = None) -> FastAPI:
    """``settings`` from the environment by default; refuses to build outside ``APP_ENV=local`` (`DT-065`)."""
    settings = load_settings() if settings is None else settings
    app = FastAPI(
        title=TITLE,
        version=__version__,
        description="API de solo lectura: expone datos cargados y resultados ya calculados; un GET nunca recalcula.",
        docs_url="/docs",
        openapi_url="/openapi.json",
        redoc_url=None,
        swagger_ui_oauth2_redirect_url=None,  # no extra public route beyond /docs and /openapi.json
    )
    app.state.settings = settings
    app.state.token_validator = validator if validator is not None else DevTokenValidator(settings.identities)
    errors.install(app)
    correlation.install(app)
    for module in (health, me, products, inventory, forecasts, recommendations, runs):
        app.include_router(module.router)
    return app
