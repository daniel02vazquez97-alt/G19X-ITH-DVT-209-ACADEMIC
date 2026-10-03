"""Batch executions (`docs/03` §16.2): read PostgreSQL, call the pure libraries, persist with
traceability. U3 adds the forecast execution (`DT-057`); U4 will add recommendations.

* `config` — the run configuration and its ``config_sha256``; standard library only.
* `forecast` — the forecast execution; needs ``psycopg`` (optional group ``db``).

Nothing is re-exported, so that `config` can be imported without ``psycopg``.
"""
