"""FastAPI application of the API V1 (`docs/07` §7, `DT-064` to `DT-068`)."""

from __future__ import annotations

from fastapi import FastAPI

from app.genai import TemplateGenerator

from . import __version__, correlation, errors
from .auth import DevTokenValidator, TokenValidator
from .routers import explanations, forecasts, health, inventory, me, products, recommendations, runs
from .settings import Settings, load_settings

TITLE = "Motor Predictivo de Abastecimiento — API V1 (solo lectura)"


def _validator(settings: Settings) -> TokenValidator:
    """``local``: development tokens (`DT-065`); ``dev``: Microsoft Entra ID access tokens (`DT-099`)."""
    if settings.entra is not None:
        from .entra import EntraTokenValidator  # optional group `entra`; never imported with APP_ENV=local

        return EntraTokenValidator(settings.entra)
    return DevTokenValidator(settings.identities)


def create_app(settings: Settings | None = None, validator: TokenValidator | None = None) -> FastAPI:
    """``settings`` from the environment by default; only ``APP_ENV=local`` and ``dev`` build (`DT-065`, `DT-099`)."""
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
    app.state.token_validator = validator if validator is not None else _validator(settings)
    app.state.text_generator = TemplateGenerator()  # U6: deterministic template (`DT-068`)
    errors.install(app)
    correlation.install(app)
    for module in (health, me, products, inventory, forecasts, recommendations, explanations, runs):
        app.include_router(module.router)
    return app
