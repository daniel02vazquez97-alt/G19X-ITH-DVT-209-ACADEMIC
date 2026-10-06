"""Container entry point of the API V1 (U7, `DT-095`).

Same behaviour as ``python -m app.api`` (`DT-065`): the configuration comes from the environment, any
``APP_ENV`` other than ``local`` is refused before the server starts, and the access log is the API's own.
The only difference is the bind address: inside the container the server listens on all interfaces so
that the ``frontend`` proxy and the healthcheck reach it; what the host sees is decided by
``infra/docker-compose.yml``, which publishes the port on 127.0.0.1 only.

U5 is not modified: this module uses its public functions ``load_settings`` and ``create_app``.
"""

from __future__ import annotations

import logging
import os
import sys

import uvicorn

from app.api.app import create_app
from app.api.settings import SettingsError, load_settings

HOST = "0.0.0.0"  # container network only; host exposure is restricted by compose
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
