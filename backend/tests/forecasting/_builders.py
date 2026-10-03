"""Hand-built requests for the provider tests: no dataset, every value chosen to be checkable."""

from __future__ import annotations

import datetime as dt

from app.forecasting import ForecastRequest

A = dt.date(2025, 12, 31)
DAY = dt.timedelta(days=1)


def daily_request(daily: list[object], as_of: dt.date = A, flags: list[bool] | None = None) -> ForecastRequest:
    """A request whose last day is ``as_of``."""
    return ForecastRequest(
        product_id=1,
        location_id=1,
        as_of_date=as_of,
        history_start=as_of - DAY * (len(daily) - 1),
        daily_consumption=tuple(daily),
        daily_stockout_flags=tuple(flags if flags is not None else [False] * len(daily)),
    )


def weekly_request(weeks: list[int], leftover: list[int] | None = None, as_of: dt.date = A) -> ForecastRequest:
    """Daily series whose anchored weekly totals are exactly ``weeks`` (each total on the week's
    first day), preceded by ``leftover`` older days that the aggregation must discard."""
    daily: list[object] = list(leftover or [])
    for total in weeks:
        daily.extend([total, 0, 0, 0, 0, 0, 0])
    return daily_request(daily, as_of)
