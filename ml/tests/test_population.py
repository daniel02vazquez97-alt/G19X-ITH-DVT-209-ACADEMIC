"""Population per cut (`DT-075` point 6 as interpreted by `DT-087`): validity on the cut, no snapshot."""

from __future__ import annotations

import datetime as _dt
import unittest
from pathlib import Path

from ml.backtest import discontinued_profile, in_population, run_backtest
from ml.config import POPULATION_AS_OF_VALIDITY, POPULATION_U3_SNAPSHOT, F5aConfig
from ml.cuts import development_cuts
from ml.data import Dataset, load_dataset
from ml.tests.fixtures import TempDataset

D = _dt.date
ASOF = POPULATION_AS_OF_VALIDITY
U3 = POPULATION_U3_SNAPSHOT
REAL = Path(__file__).resolve().parents[2] / "data" / "synthetic" / "output"


class FixturePopulationTest(unittest.TestCase):
    def setUp(self) -> None:
        with TempDataset() as path:
            self.ds = load_dataset(path)

    def test_default_rule_is_validity_on_the_cut(self) -> None:
        self.assertEqual(F5aConfig().population_rule, ASOF)

    def test_discontinued_product_before_and_after(self) -> None:
        """(a) Product 4 (inactive in the snapshot, valid until 2024-06-30) is in before and out after."""
        self.assertTrue(in_population(self.ds, (4, 1), D(2024, 3, 27), ASOF))
        self.assertTrue(in_population(self.ds, (4, 1), D(2024, 6, 30), ASOF))
        self.assertFalse(in_population(self.ds, (4, 1), D(2024, 7, 1), ASOF))
        self.assertFalse(in_population(self.ds, (4, 1), D(2024, 8, 14), ASOF))

    def test_product_starting_after_the_cut_is_out(self) -> None:
        """(b) Product 3 starts on 2023-06-01: out before, in from that day."""
        self.assertFalse(in_population(self.ds, (3, 1), D(2023, 5, 31), ASOF))
        self.assertTrue(in_population(self.ds, (3, 1), D(2023, 6, 1), ASOF))
        self.assertFalse(in_population(self.ds, (3, 1), D(2023, 5, 31), U3))

    def test_literal_u3_rule_keeps_the_previous_population(self) -> None:
        """(c) The alternative reproduces the previous default: the snapshot excludes product 4 everywhere."""
        result = run_backtest(self.ds, F5aConfig(population_rule=U3), [D(2024, 3, 27)])
        self.assertEqual(sorted(sc.key[0] for sc in result.series_cuts if sc.in_population), [1, 2, 3])
        self.assertFalse(in_population(self.ds, (4, 1), D(2024, 3, 27), U3))

    def test_discontinued_profile_reads_nothing_after_valid_to(self) -> None:
        calls = []
        real_history = Dataset.history

        def spy(ds, key, as_of):
            calls.append(as_of)
            return real_history(ds, key, as_of)

        result = run_backtest(self.ds, F5aConfig(), [D(2024, 3, 27)])
        Dataset.history = spy  # type: ignore[method-assign]
        try:
            profile = discontinued_profile(self.ds, result, F5aConfig())
        finally:
            Dataset.history = real_history  # type: ignore[method-assign]
        self.assertEqual([p["product_id"] for p in profile], [4])
        self.assertTrue(calls and all(day <= D(2024, 6, 30) for day in calls))
        self.assertEqual(profile[0]["padded_weeks"], 156)
        self.assertEqual(profile[0]["last_cut_in_population"], "2024-03-27")


@unittest.skipUnless((REAL / "products.csv").exists(), "dataset 0.4.0 not published")
class RealDatasetPopulationTest(unittest.TestCase):
    """(c) On ds-6c8ad65b4999 the literal U3 rule gives the 95 series reported before DT-087."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.ds = load_dataset(REAL)

    def _population(self, as_of: _dt.date, rule: str) -> list[int]:
        return [key[0] for key in self.ds.series_keys() if in_population(self.ds, key, as_of, rule)]

    def test_u3_rule_gives_95_at_every_cut(self) -> None:
        for as_of in development_cuts():
            population = self._population(as_of, U3)
            self.assertEqual(len(population), 95, as_of)
            self.assertNotIn(21, population)

    def test_validity_rule_keeps_the_discontinued_until_valid_to(self) -> None:
        for as_of in development_cuts():
            expected = 100 if as_of <= D(2025, 4, 2) else 95
            self.assertEqual(len(self._population(as_of, ASOF)), expected, as_of)


if __name__ == "__main__":
    unittest.main()
