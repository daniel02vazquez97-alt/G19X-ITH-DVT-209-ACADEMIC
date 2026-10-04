"""Batch executions (`docs/03` §16.2): read PostgreSQL, call the pure libraries, persist with
traceability. U3 adds the forecast execution (`DT-057`); U4 adds the recommendation execution
(`DT-058` to `DT-063`).

* `config` — the forecast run configuration and its ``config_sha256``; standard library only.
* `forecast` — the forecast execution; needs ``psycopg`` (optional group ``db``).
* `recommendation_inputs` — pure adapter of U4: rows → `EvaluationInput`; no SQL.
* `recommendation_config` — representation, ``input_sha256`` and ``config_sha256`` of U4; no SQL.
* `recommendation` — the recommendation execution; needs ``psycopg``.

Nothing is re-exported, so that the pure modules can be imported without ``psycopg``.
"""
