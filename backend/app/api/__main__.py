"""``python -m app.api`` — serve the API V1 on 127.0.0.1:8000 with uvicorn (`DT-064`, `DT-065`).

Requires ``DATABASE_URL`` and either ``APP_ENV=local`` with ``DEV_AUTH_IDENTITIES`` (`DT-065`) or
``APP_ENV=dev`` with the Entra ID identifiers (`DT-099`) in the environment; any other ``APP_ENV`` is refused
before the server starts. Exit status 1 when the configuration is refused.
"""

from __future__ import annotations

import logging
import os
import sys

import uvicorn

from .app import create_app
from .settings import SettingsError, load_settings

HOST = "127.0.0.1"
PORT = 8000


def main() -> int:
    try:
        settings = load_settings()
    except SettingsError as exc:
        print(f"REFUSED: {exc}", file=sys.stderr)
        return 1
    logging.basicConfig(level=os.environ.get("LOG_LEVEL", "INFO"), format="%(message)s")
    uvicorn.run(create_app(settings), host=HOST, port=PORT, access_log=False)
    return 0


if __name__ == "__main__":
    sys.exit(main())
