"""Configuration of the API from the environment (`DT-065`, `docs/10` §6).

``APP_ENV`` is mandatory (``local | dev | staging | prod``) and only ``local`` starts the API: there is
no Entra ID validator until Fase 8. ``DATABASE_URL`` is read with the mechanism of `app.db.connection`
(never stored in the repository); ``DEV_AUTH_IDENTITIES`` holds the fictitious development identities.
The application reads ``os.environ`` only: no ``.env`` loader.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field

from app.db.connection import ENV_VAR as DATABASE_ENV_VAR

from .auth import Identity, IdentityRegistryError, parse_identities

APP_ENVS = ("local", "dev", "staging", "prod")
LOCAL = "local"


class SettingsError(RuntimeError):
    """The API cannot start with this configuration. Messages never contain secrets."""


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str = field(repr=False)
    identities: Mapping[str, Identity] = field(repr=False)

    def __post_init__(self) -> None:
        if self.app_env not in APP_ENVS:
            raise SettingsError(f"APP_ENV must be one of {', '.join(APP_ENVS)}")
        if self.app_env != LOCAL:
            raise SettingsError(
                f"APP_ENV={self.app_env}: the development TokenValidator only runs with APP_ENV=local and "
                "there is no Entra ID validator until Fase 8 (DT-065); the API refuses to start"
            )
        if not self.database_url:
            raise SettingsError(f"{DATABASE_ENV_VAR} is not set")


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if environ is None else environ
    app_env = env.get("APP_ENV")
    if not app_env:
        raise SettingsError("APP_ENV is required (local | dev | staging | prod)")
    if app_env not in APP_ENVS:
        raise SettingsError(f"APP_ENV must be one of {', '.join(APP_ENVS)}")
    if app_env != LOCAL:
        Settings(app_env, "-", {})  # raises the explicit refusal
    database_url = env.get(DATABASE_ENV_VAR, "")
    if not database_url:
        raise SettingsError(f"{DATABASE_ENV_VAR} is not set")
    try:
        identities = parse_identities(env.get("DEV_AUTH_IDENTITIES"))
    except IdentityRegistryError as exc:
        raise SettingsError(str(exc)) from exc
    return Settings(app_env, database_url, identities)
