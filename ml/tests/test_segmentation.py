"""Syntetos-Boylan on series with a known class; training data only."""

from __future__ import annotations

import datetime as _dt
import unittest

from ml.backtest import run_series_cut
from ml.config import F5aConfig
from ml.data import load_dataset
from ml.segmentation import (
    DISCONTINUED,
    ERRATIC,
    INTERMITTENT,
    LUMPY,
    NO_DEMAND,
    SHORT_HISTORY,
    SMOOTH,
    classify,
    features,
)
from ml.tests.fixtures import TempDataset, default_quantity

CONFIG = F5aConfig()


def segment(weeks: list[float]) -> str:
    return classify(features(weeks), True, CONFIG)


class KnownClassesTest(unittest.TestCase):
    def test_four_quadrants(self) -> None:
        self.assertEqual(segment([10.0, 11.0, 9.0, 10.0] * 10), SMOOTH)
        self.assertEqual(segment([1.0, 30.0, 2.0, 25.0] * 10), ERRATIC)  # no zeros, CV² ≥ 0.49
        self.assertEqual(segment([10.0, 0.0, 0.0, 10.0] * 10), INTERMITTENT)  # ADI = 2, CV² = 0
        self.assertEqual(segment([1.0, 0.0, 0.0, 40.0] * 10), LUMPY)

    def test_features_by_hand(self) -> None:
        f = features([2.0, 0.0, 4.0, 0.0])
        self.assertEqual((f.weeks, f.nonzero_weeks, f.zero_share, f.adi), (4, 2, 0.5, 2.0))
        self.assertAlmostEqual(f.cv2, 1 / 9)  # mean 3, population variance 1

    def test_thresholds_are_inclusive_and_configurable(self) -> None:
        weeks = [3.0, 0.0, 0.0, 0.0] * 7 + [3.0, 3.0, 3.0, 3.0] * 5  # 48 weeks, 27 non-zero → ADI ≈ 1.78
        self.assertEqual(segment(weeks), INTERMITTENT)
        self.assertEqual(classify(features(weeks), True, F5aConfig(adi_threshold=2.0)), SMOOTH)

    def test_short_history_no_demand_and_discontinued(self) -> None:
        self.assertEqual(segment([5.0] * 24), SHORT_HISTORY)
        self.assertEqual(segment([0.0] * 30), NO_DEMAND)
        self.assertEqual(classify(features([5.0] * 40), False, CONFIG), DISCONTINUED)


class NoPostCutDataTest(unittest.TestCase):
    def test_segment_ignores_data_after_the_cut(self) -> None:
        cut = _dt.date(2024, 3, 27)

        def volatile_after(product: int, day: _dt.date) -> int:
            if day > cut:
                return 0 if day.toordinal() % 3 else 500
            return default_quantity(product, day)

        with TempDataset() as a, TempDataset(quantity=volatile_after) as b:
            sa = run_series_cut(load_dataset(a), (1, 1), cut, CONFIG)
            sb = run_series_cut(load_dataset(b), (1, 1), cut, CONFIG)
        self.assertEqual((sa.segment, sa.feats), (sb.segment, sb.feats))
        self.assertEqual(sa.segment, SMOOTH)


if __name__ == "__main__":
    unittest.main()
