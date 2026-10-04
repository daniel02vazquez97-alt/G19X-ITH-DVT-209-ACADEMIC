"""Pagination and ordering of the list endpoints (`docs/07` §1, `DT-066`)."""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Query

from .errors import ApiError

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


@dataclass(frozen=True)
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(
    page: int = Query(1, ge=1, description="Página, desde 1"),
    page_size: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Tamaño de página (1–200)"),
) -> PageParams:
    return PageParams(page, page_size)


@dataclass(frozen=True)
class Sort:
    field: str
    descending: bool


def parse_sort(value: str | None, allowed: tuple[str, ...], default: str) -> Sort:
    """``sort=<field>`` or ``sort=-<field>``; only the documented fields; otherwise 400 ``INVALID_SORT``."""
    text = default if value is None else value
    descending = text.startswith("-")
    name = text[1:] if descending else text
    if name not in allowed:
        raise ApiError(400, "INVALID_SORT", "Campo de ordenación no admitido.", {"allowed": list(allowed)})
    return Sort(name, descending)
