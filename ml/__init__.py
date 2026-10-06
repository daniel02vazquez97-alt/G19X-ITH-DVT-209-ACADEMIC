"""Phase 5 training and evaluation component (`docs/03` §16.2, `DT-072`).

F5a (`DT-086`): backtesting (`DT-075`), Level 1 metrics (`DT-076`), provisional segmentation
(`DT-077`) and provisional simple exponential smoothing (`DT-076` point 7), applied to the U3
baselines. F5b (`DT-088`): the Level 2 simulator in ``ml.simulation``. F5c (`DT-092`): candidate models
(``ml.candidates``), the `DT-011` study and the intervals of US-055 in ``ml.f5c``. Standard library only (`DT-073`); ``float`` is allowed inside this package and never
crosses into U1 or U3 (`DT-074`).

Uses ``app.forecasting`` and ``app.supply_engine`` as libraries, reads the published dataset read-only
and never writes to the database. Run from the repository root with ``PYTHONPATH=backend``::

    python -m ml backtest --data data/synthetic/output
"""

#: Version of the evaluation code; recorded in every report (0.1.0: F5a and F5b; 0.2.0: F5c).
ML_VERSION = "0.2.0"
