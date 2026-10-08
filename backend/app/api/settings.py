"""Configuration of the API from the environment (`DT-065`, `DT-099`, `docs/10` §6).

``APP_ENV`` is mandatory (``local | dev | staging | prod``):

* ``local`` — development `TokenValidator` with the fictitious identities of ``DEV_AUTH_IDENTITIES``; no
  Azure, no Entra ID, nothing else required (RNF-006). Unchanged since U5.
* ``dev`` — Microsoft Entra ID (U11, `DT-099`): ``ENTRA_TENANT_ID``, ``ENTRA_API_CLIENT_ID`` and
  ``ENTRA_SPA_CLIENT_ID`` are required (identifiers, not secrets), ``DEV_AUTH_IDENTITIES`` must be absent or
  empty, and the optional group ``entra`` of ``pyproject.toml`` must be installed.
* ``staging`` and ``prod`` still refuse to start: no unit has authorized them.

``DATABASE_URL`` is read with the mechanism of `app.db.connection` (never stored in the repository). The
application reads ``os.environ`` only: no ``.env`` loader. Any refusal happens before the server starts.
"""

from __future__ import annotations

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from app.db.connection import ENV_VAR as DATABASE_ENV_VAR

from .auth import Identity, IdentityRegistryError, parse_identities

APP_ENVS = ("local", "dev", "staging", "prod")
LOCAL = "local"
DEV = "dev"
STARTABLE_ENVS = (LOCAL, DEV)
ENTRA_VARS = ("ENTRA_TENANT_ID", "ENTRA_API_CLIENT_ID", "ENTRA_SPA_CLIENT_ID")


class SettingsError(RuntimeError):
    """The API cannot start with this configuration. Messages never contain secrets."""


@dataclass(frozen=True)
class Settings:
    app_env: str
    database_url: str = field(repr=False)
    identities: Mapping[str, Identity] = field(repr=False)
    #: Only with ``APP_ENV=dev``: an ``app.api.entra.EntraConfig`` (`DT-099`).
    entra: Any = None

    def __post_init__(self) -> None:
        if self.app_env not in APP_ENVS:
            raise SettingsError(f"APP_ENV must be one of {', '.join(APP_ENVS)}")
        if self.app_env not in STARTABLE_ENVS:
            raise SettingsError(
                f"APP_ENV={self.app_env}: only local (development identities) and dev (Microsoft Entra ID, "
                "DT-099) are authorized; the API refuses to start"
            )
        if self.app_env == LOCAL and self.entra is not None:
            raise SettingsError("APP_ENV=local never uses Entra ID")
        if self.app_env == DEV and (self.entra is None or self.identities):
            raise SettingsError("APP_ENV=dev requires the Entra ID configuration and no development identities")
        if not self.database_url:
            raise SettingsError(f"{DATABASE_ENV_VAR} is not set")


def load_settings(environ: Mapping[str, str] | None = None) -> Settings:
    env = os.environ if environ is None else environ
    app_env = env.get("APP_ENV")
    if not app_env:
        raise SettingsError("APP_ENV is required (local | dev | staging | prod)")
    if app_env not in APP_ENVS:
        raise SettingsError(f"APP_ENV must be one of {', '.join(APP_ENVS)}")
    if app_env not in STARTABLE_ENVS:
        Settings(app_env, "-", {})  # raises the explicit refusal
    database_url = env.get(DATABASE_ENV_VAR, "")
    if not database_url:
        raise SettingsError(f"{DATABASE_ENV_VAR} is not set")
    if app_env == DEV:
        return Settings(app_env, database_url, {}, _entra_config(env))
    try:
        identities = parse_identities(env.get("DEV_AUTH_IDENTITIES"))
    except IdentityRegistryError as exc:
        raise SettingsError(str(exc)) from exc
    return Settings(app_env, database_url, identities)


def _entra_config(env: Mapping[str, str]) -> Any:
    """``APP_ENV=dev``: the Entra ID identifiers, or a refusal that names the missing piece (no values)."""
    if env.get("DEV_AUTH_IDENTITIES"):
        raise SettingsError("DEV_AUTH_IDENTITIES is only accepted with APP_ENV=local; unset it for APP_ENV=dev")
    missing = [name for name in ENTRA_VARS if not env.get(name)]
    if missing:
        raise SettingsError(f"APP_ENV=dev requires {', '.join(missing)}")
    try:
        from .entra import EntraConfig, EntraConfigError  # needs the optional group `entra` (PyJWT)
    except ImportError as exc:
        raise SettingsError("APP_ENV=dev requires the optional group entra of backend/pyproject.toml (PyJWT)") from exc
    try:
        return EntraConfig(env["ENTRA_TENANT_ID"], env["ENTRA_API_CLIENT_ID"], env["ENTRA_SPA_CLIENT_ID"])
    except EntraConfigError as exc:
        raise SettingsError(f"invalid Entra ID configuration: {exc}") from exc
