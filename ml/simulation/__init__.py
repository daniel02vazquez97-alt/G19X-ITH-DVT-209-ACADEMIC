"""F5b: Level 2 simulator applied to the four baselines (`DT-080`, `DT-088`, US-058).

* `environment` — the only module that reads the latent demand (``demand.csv``, SYNTHETIC only) and the
  physics of a simulated day (receipts, demand, consumption, lost sales).
* `forecasters` — the weekly point forecast of each branch on its own simulated history.
* `engine_inputs` — the U1 ``EvaluationInput`` at a decision date (same mapping as the pure U4 adapter).
* `simulator` — closed loop of every branch, product by product.
* `level2` — Level 2 metrics, aggregates and the informative cross of `DT-078`.
* `report` — deterministic outputs, Markdown report and compact JSON.

Exact arithmetic (``Decimal``/``Fraction``) everywhere in the simulation and in the call to U1; ``float``
only inside the models and the metrics (`DT-074`). Nothing after 2025-09-24 is read (`DT-075`).
"""
