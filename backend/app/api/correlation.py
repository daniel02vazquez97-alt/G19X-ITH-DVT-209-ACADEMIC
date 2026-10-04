"""``X-Correlation-ID`` (`DT-066`): accepted from the client if valid, generated otherwise, returned always.

The middleware also writes one structured (JSON) access log line per request and turns any unhandled
exception into the uniform 500, so that even that response carries the correlation id. It never logs
headers, tokens or bodies (`docs/10` §4 and §12).
"""

from __future__ import annotations

import json
import logging
import re
import time
import uuid

from fastapi import FastAPI, Request
from starlette.middleware.base import BaseHTTPMiddleware

from .errors import internal_error

HEADER = "X-Correlation-ID"
PATTERN = re.compile(r"[A-Za-z0-9._-]{8,64}")

access_logger = logging.getLogger("app.api.access")
error_logger = logging.getLogger("app.api")


def resolve(value: str | None) -> str:
    """The client's value if it matches ``^[A-Za-z0-9._-]{8,64}$``; otherwise a new UUID4."""
    if value is not None and PATTERN.fullmatch(value):
        return value
    return str(uuid.uuid4())


class CorrelationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):  # type: ignore[override]
        correlation_id = resolve(request.headers.get(HEADER))
        request.state.correlation_id = correlation_id
        request.state.subject_id = None
        started = time.perf_counter()
        try:
            response = await call_next(request)
        except Exception:  # noqa: BLE001 — unhandled: generic 500, details only in the server log
            error_logger.exception("unhandled error (correlation_id=%s)", correlation_id)
            response = internal_error(request)
        response.headers[HEADER] = correlation_id
        route = request.scope.get("route")
        access_logger.info(
            json.dumps(
                {
                    "correlation_id": correlation_id,
                    "subject_id": getattr(request.state, "subject_id", None),
                    "method": request.method,
                    "route": getattr(route, "path", request.url.path),
                    "status": response.status_code,
                    "duration_ms": round((time.perf_counter() - started) * 1000, 3),
                },
                sort_keys=True,
            )
        )
        return response


def install(app: FastAPI) -> None:
    app.add_middleware(CorrelationMiddleware)
