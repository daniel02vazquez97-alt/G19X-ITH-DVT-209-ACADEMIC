"""No leakage: altering anything after the cut changes the truth, never the training side."""

from __future__ import annotations

import datetime as _dt
import unittest

from ml.backtest import run_series_cut
from ml.config import F5aConfig
from ml.data import load_dataset
from ml.tests.fixtures import DEFAULT_ORDERS, TempDataset, default_quantity, default_stockout

CUT = _dt.date(2024, 8, 14)


def altered_quantity(product: int, day: _dt.date) -> int:
    base = default_quantity(product, day)
    return base * 7 + 50 if day > CUT else base


def altered_stockout(product: int, day: _dt.date) -> bool:
    return True if day > CUT else default_stockout(product, day)


# A fast order issued before the cut but completed after it, plus one entirely after the cut.
ALTERED_ORDERS = DEFAULT_ORDERS + [
    (8, 1, "2024-08-10", [("2024-08-16", 40)], 40, 1),
    (9, 1, "2024-09-01", [("2024-09-02", 40)], 40, 1),
]


def training_side(sc) -> tuple:
    return (
        sc.in_population,
        sc.exclusion_reason,
        sc.segment,
        sc.feats,
        sc.scale_abs,
        sc.scale_sq,
        sc.protection,
        sc.forecasts,
    )


class LeakageTest(unittest.TestCase):
    def test_post_cut_changes_do_not_change_predictions(self) -> None:
        config = F5aConfig()
        with TempDataset() as a, TempDataset(quantity=altered_quantity, stockout=altered_stockout, orders=ALTERED_ORDERS) as b:
            ds_a, ds_b = load_dataset(a), load_dataset(b)
        self.assertNotEqual(ds_a.lead_time_observations, ds_b.lead_time_observations)
        for key in ds_a.series_keys():
            sa, sb = run_series_cut(ds_a, key, CUT, config), run_series_cut(ds_b, key, CUT, config)
            self.assertEqual(training_side(sa), training_side(sb), key)
            if sa.truth:
                self.assertNotEqual(sa.truth, sb.truth, key)  # the alteration is visible in the truth only

    def test_pre_cut_change_is_detected(self) -> None:
        """Sanity check of the instrument: a change before the cut does change the forecasts."""

        def earlier(product: int, day: _dt.date) -> int:
            return default_quantity(product, day) + (40 if day == CUT else 0)

        config = F5aConfig()
        with TempDataset() as a, TempDataset(quantity=earlier) as b:
            sa = run_series_cut(load_dataset(a), (1, 1), CUT, config)
            sb = run_series_cut(load_dataset(b), (1, 1), CUT, config)
        self.assertNotEqual(sa.forecasts, sb.forecasts)


if __name__ == "__main__":
    unittest.main()
