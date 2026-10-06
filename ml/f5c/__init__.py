"""F5c (`DT-092`): candidate models, the `DT-011` study and the intervals of US-055, on SYNTHETIC data.

* `config` — every provisional value of F5c and the accepted criteria of `DT-093`, in one place.
* `strategies` — training data under the strategies (a), (b) and (c) of `DT-081` (`DT-093` point 8).
* `backtest` — Level 1 of the 17 cuts for the baselines, SES and the candidates, plus the weekly records of US-055.
* `study` — the `DT-011` study (Level 1 against observed consumption and, SYNTHETIC only, latent demand).
* `intervals` — coverage of the current interval and of a variant calibrated per horizon on earlier cuts.
* `criteria` — the automatic table of `DT-091` / `DT-093` per candidate, without any promotion.
* `run` and `report` — orchestration with a resumable cache, the Markdown report and its compact JSON.

Nothing reads the holdout (`DT-075`), nothing is written to the database and nothing is promoted (`DT-084`).
"""
