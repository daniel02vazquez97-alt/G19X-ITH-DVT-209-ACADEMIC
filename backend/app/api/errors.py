"""Uniform error contract (`docs/07` §1, `DT-066`): ``{"error": {code, message, details, correlation_id}}``.

Never a trace, SQL, host, configuration fragment or received value.
"""

from __future__ import annotations

import logging
from typing import Any

import psycopg
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = logging.getLogger("app.api")

#: Default code and message per HTTP status (`docs/07` §1).
STATUS_ERRORS: dict[int, tuple[str, str]] = {
    400: ("INVALID_PARAMETER", "La petición no es válida."),
    401: ("AUTHENTICATION_REQUIRED", "Se requiere autenticación."),
    403: ("FORBIDDEN", "No tiene permiso para este recurso."),
    404: ("NOT_FOUND", "El recurso no existe."),
    405: ("METHOD_NOT_ALLOWED", "Método no permitido: la API V1 es de solo lectura."),
    409: ("CONFLICT", "Conflicto con el estado del recurso."),
    422: ("VALIDATION_ERROR", "Los parámetros no superan la validación."),
    429: ("TOO_MANY_REQUESTS", "Demasiadas peticiones."),
    500: ("INTERNAL_ERROR", "Error interno."),
    503: ("SERVICE_UNAVAILABLE", "Servicio no disponible temporalmente."),
}


class ApiError(Exception):
    def __init__(
        self,
        status: int,
        code: str,
        message: str,
        details: dict[str, Any] | list[Any] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(code)
        self.status = status
        self.code = code
        self.message = message
        self.details = details if details is not None else {}
        self.headers = headers


def error_response(
    request: Request,
    status: int,
    code: str,
    message: str,
    details: dict[str, Any] | list[Any] | None = None,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    body = {"error": {"code": code, "message": message, "details": details if details is not None else {},
                      "correlation_id": correlation_id}}
    return JSONResponse(status_code=status, content=body, headers=headers)


def internal_error(request: Request) -> JSONResponse:
    code, message = STATUS_ERRORS[500]
    return error_response(request, 500, code, message)


async def _api_error(request: Request, exc: ApiError) -> JSONResponse:
    return error_response(request, exc.status, exc.code, exc.message, exc.details, exc.headers)


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    details = [
        {"field": ".".join(str(part) for part in error.get("loc", ())[1:]) or str(error.get("loc", ("",))[0]),
         "issue": error.get("type", "invalid")}
        for error in exc.errors()
    ]
    code, message = STATUS_ERRORS[422]
    return error_response(request, 422, code, message, details)


async def _http_error(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code, message = STATUS_ERRORS.get(exc.status_code, STATUS_ERRORS[500])
    status = exc.status_code if exc.status_code in STATUS_ERRORS else 500
    return error_response(request, status, code, message, headers=getattr(exc, "headers", None))


async def _database_unavailable(request: Request, exc: psycopg.OperationalError) -> JSONResponse:
    logger.error("database unavailable: %s", type(exc).__name__)
    code, message = STATUS_ERRORS[503]
    return error_response(request, 503, code, message)


def install(app: FastAPI) -> None:
    app.add_exception_handler(ApiError, _api_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(StarletteHTTPException, _http_error)
    app.add_exception_handler(psycopg.OperationalError, _database_unavailable)
