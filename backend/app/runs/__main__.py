"""``python -m app.runs forecast --as-of AAAA-MM-DD`` — forecast execution on ``DATABASE_URL``.

Exit status 0 for ``COMPLETED`` and ``ALREADY_COMPUTED``, 1 for ``FAILED`` or a refused execution,
2 for a usage error.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import sys

from app.db.connection import connect

from .forecast import ForecastRunError, run_forecast


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
    args = parser.parse_args(argv)

    with connect() as conn:
        try:
            result = run_forecast(conn, args.as_of)
        except ForecastRunError as exc:
            print(f"REFUSED: {exc}", file=sys.stderr)
            return 1
    summary = result.summary
    print(f"{result.outcome}: calculation_run {result.calculation_run_id}, as_of_date {result.as_of_date}")
    if result.error is not None:
        print(f"  error: {result.error}", file=sys.stderr)
    for key in ("dataset_version", "eligible", "excluded_count", "forecasted", "fallback_count",
                "no_forecast_count", "forecast_rows", "primary_rows"):
        if key in summary:
            print(f"  {key}: {summary[key]}")
    return 0 if result.outcome.ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
