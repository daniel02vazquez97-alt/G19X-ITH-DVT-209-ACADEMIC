"""Configuration of a forecast execution and its deterministic identity (`DT-057` point 3).

``config_sha256`` is the SHA-256 of the canonical JSON (sorted keys, compact separators, UTF-8) of
everything that determines the output: models with their hyperparameters, reference, primary chain,
horizon, quantization, catalog policy. No timestamps, ids or random values enter it.
"""

from __future__ import annotations

import datetime as _dt
import hashlib
import json
from typing import Any

from app.forecasting import (
    BASELINES,
    CONFIDENCE_LEVEL,
    HORIZON_WEEKS,
    METHOD_USED,
    PRIMARY_CHAIN,
    QUANTIZATION_SCALE,
    REFERENCE,
)

RUN_TYPE = "FORECAST"
GRANULARITY = "WEEKLY"
#: Catalog policy of `DT-056` point 10.
CATALOG_POLICY = "ACTIVE_AND_VALID_AT_AS_OF_WITH_CONTIGUOUS_HISTORY"


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def run_configuration() -> dict[str, Any]:
    """Everything that determines the persisted output of a forecast execution."""
    return {
        "run_type": RUN_TYPE,
        "models": [
            {
                "name": d.name,
                "version": d.version,
                "algorithm": d.algorithm,
                "hyperparameters": d.hyperparameters,
            }
            for d in BASELINES
        ],
        "reference": {"name": REFERENCE.name, "version": REFERENCE.version},
        "primary_chain": [d.name for d in PRIMARY_CHAIN],
        "horizon_weeks": HORIZON_WEEKS,
        "granularity": GRANULARITY,
        "method_used": METHOD_USED,
        "confidence_level": str(CONFIDENCE_LEVEL),
        "quantization": {"scale": QUANTIZATION_SCALE, "rounding": "ROUND_HALF_EVEN"},
        "catalog_policy": CATALOG_POLICY,
    }


def config_sha256(configuration: dict[str, Any] | None = None) -> str:
    text = canonical_json(run_configuration() if configuration is None else configuration)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def lock_key(as_of_date: _dt.date, data_load_id: int, sha256: str) -> int:
    """Advisory-lock key of one logical execution: a signed 64-bit integer from its identity."""
    identity = canonical_json([RUN_TYPE, as_of_date.isoformat(), data_load_id, sha256])
    digest = hashlib.sha256(identity.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big", signed=True)
