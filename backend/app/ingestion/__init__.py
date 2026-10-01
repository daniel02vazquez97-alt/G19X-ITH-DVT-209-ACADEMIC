"""U2 — Ingestion of the synthetic dataset 0.4.0 into PostgreSQL (`DT-044`, `DT-055`, `docs/04` §9).

Consumes the generator's *contract*, never its code: nothing is imported from ``data/synthetic``.

* `contract`, `dataset`, `mapping` — file and row validation; standard library only.
* `loader` — the load itself (``load_dataset``); needs ``psycopg`` (optional group ``db``).

Nothing is re-exported here, so that the pure modules can be imported without ``psycopg``.
"""
