"""FastAPI application of the API V1 (`docs/07` §7, `DT-064` to `DT-068`)."""

from __future__ import annotations

from fastapi import FastAPI

import os

from app.genai import ChatGenerator, TemplateGenerator, TextGenerator

from . import __version__, correlation, errors
from .auth import DevTokenValidator, TokenValidator
from .assistant import Assistant, build_assistant
from .routers import assistant, explanations, forecasts, health, inventory, me, products, recommendations, runs
from .settings import Settings, load_settings

TITLE = "Motor Predictivo de Abastecimiento — API V1 (solo lectura)"


def _validator(settings: Settings) -> TokenValidator:
    """``local``: development tokens (`DT-065`); ``dev``: Microsoft Entra ID access tokens (`DT-099`)."""
    if settings.entra is not None:
        from .entra import EntraTokenValidator  # optional group `entra`; never imported with APP_ENV=local

        return EntraTokenValidator(settings.entra)
    return DevTokenValidator(settings.identities)


def _generators(settings: Settings) -> tuple[TextGenerator, TextGenerator | None]:
    """(generator, fallback): the template alone (U6), or Azure OpenAI with the template as fallback (`DT-101`)."""
    if settings.genai is None:
        return TemplateGenerator(), None
    from .azure_openai import AzureOpenAIChat, ManagedIdentityToken

    token = ManagedIdentityToken(settings.genai, os.environ)
    chat = AzureOpenAIChat(settings.genai, token.get)
    return ChatGenerator(chat, f"azure-openai/{settings.genai.deployment}"), TemplateGenerator()


def _assistant(settings: Settings) -> Assistant | None:
    """U15b (`DT-103`): the documentary assistant, with the U13 model when it is configured (own call budget)."""
    if settings.genai is None:
        return build_assistant(settings, None, None)
    from .azure_openai import AzureOpenAIChat, ManagedIdentityToken

    chat = AzureOpenAIChat(settings.genai, ManagedIdentityToken(settings.genai, os.environ).get)
    return build_assistant(settings, chat, f"azure-openai/{settings.genai.deployment}")


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
    # U6: deterministic template (`DT-068`); U13: Azure OpenAI with the template as fallback (`DT-101`).
    app.state.text_generator, app.state.text_fallback = _generators(settings)
    app.state.assistant = _assistant(settings)  # U15b (`DT-103`); None -> 503
    errors.install(app)
    correlation.install(app)
    for module in (health, me, products, inventory, forecasts, recommendations, explanations, runs, assistant):
        app.include_router(module.router)
    return app
