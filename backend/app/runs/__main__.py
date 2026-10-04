"""Batch executions on ``DATABASE_URL``.

* ``python -m app.runs forecast --as-of AAAA-MM-DD`` — forecast execution of U3 (`DT-057`).
* ``python -m app.runs recommend --as-of AAAA-MM-DD`` — recommendation execution of U4 (`DT-058` to
  `DT-063`); it consumes the forecast execution of the same cut and never launches it.

Exit status 0 for ``COMPLETED`` and ``ALREADY_COMPUTED``, 1 for ``FAILED`` or a refused execution,
2 for a usage error.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys

from app.db.connection import connect

from .forecast import ForecastRunError, run_forecast

_FORECAST_KEYS = ("dataset_version", "eligible", "excluded_count", "forecasted", "fallback_count",
                  "no_forecast_count", "forecast_rows", "primary_rows")
_RECOMMEND_KEYS = ("dataset_version", "data_load_id", "forecast_run_id", "engine_version", "policy_set",
                   "input_rules_version", "candidates", "evaluated", "by_outcome", "by_reason", "by_flag", "rows")


def _date(text: str) -> _dt.date:
    try:
        return _dt.date.fromisoformat(text)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"not a date AAAA-MM-DD: {text}") from exc


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(prog="python -m app.runs")
    commands = parser.add_subparsers(dest="command", required=True)
    forecast_parser = commands.add_parser("forecast", help="forecast every eligible series at a cut")
    forecast_parser.add_argument("--as-of", required=True, type=_date, dest="as_of")
    recommend_parser = commands.add_parser(
        "recommend", help="evaluate every product-location at the cut of the data load (U4)"
    )
    recommend_parser.add_argument("--as-of", required=True, type=_date, dest="as_of")
    args = parser.parse_args(argv)

    if args.command == "recommend":
        from .recommendation import RecommendationRunError, run_recommendations

        refused: tuple[type[Exception], ...] = (RecommendationRunError,)
        run, keys = run_recommendations, _RECOMMEND_KEYS
    else:
        refused, run, keys = (ForecastRunError,), run_forecast, _FORECAST_KEYS
    with connect() as conn:
        try:
            result = run(conn, args.as_of)
        except refused as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 1
    summary = result.summary
    print(f"{result.outcome}: calculation_run {result.calculation_run_id}, as_of_date {result.as_of_date}")
    if result.error is not None:
        print(f"  error: {result.error}", file=sys.stderr)
    for key in keys:
        if key in summary:
            print(f"  {key}: {summary[key]}")
    return 0 if result.outcome.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
