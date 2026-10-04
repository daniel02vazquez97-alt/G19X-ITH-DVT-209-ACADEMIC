"""API V1 de solo lectura (U5): `docs/07` §7, `DT-064` a `DT-067`.

The API reads what U2–U4 persisted and never recalculates: it does not import `supply_engine`,
`forecasting` nor `runs` (`docs/03` §16.4). Authentication is local until Fase 8: a development
`TokenValidator` that only runs with ``APP_ENV=local`` (`DT-065`).
"""

#: Version of the application reported by ``GET /health``; equal to ``backend/pyproject.toml``.
__version__ = "0.0.0"
