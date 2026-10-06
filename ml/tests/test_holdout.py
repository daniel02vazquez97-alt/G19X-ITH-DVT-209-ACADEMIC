"""Calendar of `DT-075` and the holdout guard: no path reads data after 2025-09-24."""

from __future__ import annotations

import datetime as _dt
import unittest
from pathlib import Path
from unittest import mock

from ml import cuts
from ml.backtest import run_backtest
from ml.config import F5aConfig
from ml.cuts import HoldoutAccessError, check_cut, development_cuts, evaluation_end, week_end
from ml.data import Dataset, load_dataset
from ml.tests.fixtures import TempDataset

D = _dt.date


class CalendarTest(unittest.TestCase):
    def test_seventeen_cuts_every_four_weeks(self) -> None:
        cut_dates = development_cuts()
        self.assertEqual(len(cut_dates), 17)
        self.assertEqual(cut_dates[0], D(2024, 3, 27))
        self.assertEqual(cut_dates[-1], D(2025, 6, 18))
        self.assertTrue(all((b - a).days == 28 for a, b in zip(cut_dates, cut_dates[1:])))

    def test_week_anchors(self) -> None:
        self.assertEqual(week_end(156), D(2025, 12, 31))
        self.assertEqual(week_end(142), D(2025, 9, 24))
        self.assertEqual(week_end(64), D(2024, 3, 27))
        self.assertEqual(cuts.HOLDOUT_CUT, week_end(142))

    def test_windows_end_before_the_holdout(self) -> None:
        for as_of in development_cuts():
            check_cut(as_of)
            self.assertLessEqual(evaluation_end(as_of), cuts.LAST_READABLE_DATE)
            # Training (≤ as_of) and evaluation (> as_of) never overlap; no dead zone.
            self.assertEqual((evaluation_end(as_of) - as_of).days, 7 * 14)
        self.assertEqual(evaluation_end(development_cuts()[-1]), D(2025, 9, 24))

    def test_holdout_cut_and_invading_cuts_raise(self) -> None:
        for as_of in (D(2025, 9, 24), D(2025, 10, 1), D(2025, 6, 25), D(2025, 6, 19)):
            with self.assertRaises(HoldoutAccessError):
                check_cut(as_of)


class LoaderGuardTest(unittest.TestCase):
    def test_rows_after_the_limit_are_discarded(self) -> None:
        with TempDataset() as path:
            ds = load_dataset(path)
        for key in ds.series_keys():
            last = ds.last_day(key)
            if last is not None:
                self.assertLessEqual(last, D(2025, 9, 24))
        # Order 6 completes on 2025-10-02: invisible, even though a receipt precedes the limit.
        self.assertNotIn(D(2025, 9, 10), {o.issued_on for o in ds.lead_time_observations})

    def test_reading_after_the_limit_raises(self) -> None:
        with TempDataset() as path:
            ds = load_dataset(path)
        with self.assertRaises(HoldoutAccessError):
            ds.window((1, 1), D(2025, 9, 20), D(2025, 9, 25))
        with self.assertRaises(HoldoutAccessError):
            ds.history((1, 1), D(2025, 9, 25))
        self.assertIsNotNone(ds.window((1, 1), D(2025, 9, 18), D(2025, 9, 24)))

    def test_backtest_refuses_the_holdout_cut_before_reading(self) -> None:
        with TempDataset() as path:
            ds = load_dataset(path)
        with mock.patch.object(Dataset, "history", side_effect=AssertionError("read")) as history:
            with self.assertRaises(HoldoutAccessError):
                run_backtest(ds, F5aConfig(), [D(2024, 3, 27), D(2025, 9, 24)])
            history.assert_not_called()

    def test_demand_csv_is_never_opened(self) -> None:
        opened: list[str] = []
        real_open = Path.open

        def spy(self: Path, *args, **kwargs):
            opened.append(self.name)
            return real_open(self, *args, **kwargs)

        with TempDataset() as path, mock.patch.object(Path, "open", spy):
            ds = load_dataset(path)
            run_backtest(ds, F5aConfig(), [D(2024, 3, 27)])
        self.assertNotIn("demand.csv", opened)
        self.assertIn("consumption.csv", opened)


if __name__ == "__main__":
    unittest.main()
