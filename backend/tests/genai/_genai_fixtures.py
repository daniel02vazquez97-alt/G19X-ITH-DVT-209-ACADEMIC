"""Persisted rows of the real run (dataset 0.4.0, cut 2025-12-31), copied from ``recommendations``.

Ids 4 (RECOMMEND, ``ORDER_MULTIPLE_ROUNDING``), 46 (NO_NEED, ``UNCOUNTED_TRANSIT``) and 3 (NOT_CALCULABLE,
``NO_ACTIVE_PREFERRED_SUPPLIER``): ``calculation_inputs.breakdown`` exactly as U4 stored it.
"""

from __future__ import annotations

import copy
import datetime as dt
from typing import Any

PROVENANCE: dict[str, Any] = {
    "data_origin": "SYNTHETIC",
    "dataset_version": "ds-6c8ad65b4999",
    "generator_version": "0.4.0",
    "data_load_id": 1,
    "as_of_date": dt.date(2025, 12, 31),
    "run_id": 2,
    "engine_version": "0.1.0",
    "policy_set": "V1_PROVISIONAL",
    "forecast_run_id": 1,
    "notices": ["SYNTHETIC_DATA", "V1_PROVISIONAL_POLICY"],
}

_B3_NULL = {"a": None, "b": None, "d": None, "p": None, "s1": None, "s2": None}

RECOMMEND_ROW: dict[str, Any] = {
    "recommendation_id": 4, "run_id": 2, "outcome": "RECOMMEND", "flags": ["ORDER_MULTIPLE_ROUNDING"],
    "reasons": [], "missing_policy_parameters": [], "unit_of_measure": "BOX",
    "breakdown": {
        "a": "80464966106", "b": "87626348089434", "d": "21300", "p": "238877404/109375", "z": "1.65",
        "s1": "2113603", "s2": "4270218411", "moq": "1", "q_moq": "2623.500600092591729239380374",
        "on_hand": "242", "q_final": "2700", "sigma_h": "266.3506791903153337381526076",
        "raw_need": "2623.500600092591729239380374", "reserved": "0", "as_of_date": "2025-12-31",
        "supplier_id": "10", "safety_stock": "439.4786206640203006679518026",
        "target_level": "2865.500600092591729239380374", "horizon_start": "2026-01-01", "lead_time_days": "25",
        "order_multiple": "100", "effective_lines": [], "lead_time_source": "OBSERVED", "total_in_transit": "0",
        "review_period_days": "7", "sigma_window_count": "1065", "demand_over_horizon": "265346154/109375",
        "effective_in_transit": "0", "coverage_horizon_days": "32", "demand_over_lead_time": "132673077/70000",
        "demand_conversion_rule": "V1-04", "uncapped_lead_time_days": "25", "inventory_position_decision": "242",
        "lead_time_observation_count": "12", "inventory_position_accounting": "242",
    },
}

NO_NEED_ROW: dict[str, Any] = {
    "recommendation_id": 46, "run_id": 2, "outcome": "NO_NEED", "flags": ["UNCOUNTED_TRANSIT"],
    "reasons": [], "missing_policy_parameters": [], "unit_of_measure": "KG",
    "breakdown": {
        "a": "1684032", "b": "1833910848", "d": "21180", "p": "-8", "z": "1.65", "s1": "79800", "s2": "6014848",
        "moq": "25", "q_moq": None, "on_hand": "39", "q_final": None, "sigma_h": "1.225403763305688728630637860",
        "raw_need": "0", "reserved": "0", "as_of_date": "2025-12-31", "supplier_id": "1",
        "safety_stock": "2.021916209454386402240552468", "target_level": "78.02191620945438640224055247",
        "horizon_start": "2026-01-01", "lead_time_days": "31", "order_multiple": "5",
        "effective_lines": [{"item_id": "3561", "expected_on": "2026-01-20", "supplier_id": "1",
                             "quantity_pending": "45", "purchase_order_id": "3561"}],
        "lead_time_source": "OBSERVED", "total_in_transit": "90", "review_period_days": "7",
        "sigma_window_count": "1059", "demand_over_horizon": "76", "effective_in_transit": "45",
        "coverage_horizon_days": "38", "demand_over_lead_time": "62", "demand_conversion_rule": "V1-04",
        "uncapped_lead_time_days": "31", "inventory_position_decision": "84", "lead_time_observation_count": "12",
        "inventory_position_accounting": "129",
    },
}

NOT_CALCULABLE_ROW: dict[str, Any] = {
    "recommendation_id": 3, "run_id": 2, "outcome": "NOT_CALCULABLE", "flags": [],
    "reasons": ["NO_ACTIVE_PREFERRED_SUPPLIER"], "missing_policy_parameters": [], "unit_of_measure": "EACH",
    "breakdown": {
        **_B3_NULL, "z": "1.65", "moq": None, "q_moq": None, "on_hand": "0", "q_final": None, "sigma_h": None,
        "raw_need": None, "reserved": "0", "as_of_date": "2025-12-31", "supplier_id": None, "safety_stock": None,
        "target_level": None, "horizon_start": "2026-01-01", "lead_time_days": None, "order_multiple": None,
        "effective_lines": None, "lead_time_source": None, "total_in_transit": "0", "review_period_days": "7",
        "sigma_window_count": None, "demand_over_horizon": None, "effective_in_transit": None,
        "coverage_horizon_days": None, "demand_over_lead_time": None, "demand_conversion_rule": None,
        "uncapped_lead_time_days": None, "inventory_position_decision": None, "lead_time_observation_count": None,
        "inventory_position_accounting": "0",
    },
}

PROVISIONAL = ("Aviso: las cifras son provisionales, calculadas con datos sintéticos y con la política provisional "
               "de la primera versión; no constituyen una recomendación de negocio definitiva.")

#: Hand-computed displays: 265346154/109375 = 2426.0219794…; 439.47862066… → 439.478621;
#: 2623.5006000925… → 2623.500600 → 2623.5006; 78.0219162094… → 78.021916; 2.0219162094… → 2.021916.
RECOMMEND_TEXT = (
    "Se sugiere pedir 2700 BOX. La posición de inventario para la decisión es de 242 BOX: 242 en existencia, más 0 "
    "en tránsito que llega dentro del horizonte, menos 0 reservados. El nivel objetivo es de 2865.5006 BOX: la "
    "demanda prevista para los próximos 32 días, de 2426.021979 BOX, más un stock de seguridad de 439.478621 BOX. "
    "Ese horizonte suma el plazo de entrega, de 25 días (observado en las recepciones del proveedor), y el periodo "
    "de revisión, de 7 días. La necesidad bruta es de 2623.5006 BOX. La cantidad se redondea hacia arriba al "
    "múltiplo de compra de 100 BOX, desde 2623.5006 BOX. " + PROVISIONAL
)
NO_NEED_TEXT = (
    "No se sugiere pedido: la posición de inventario para la decisión, de 84 KG (39 en existencia, más 45 en "
    "tránsito que llega dentro del horizonte, menos 0 reservados), cubre el nivel objetivo de 78.021916 KG. Ese "
    "nivel es la demanda prevista para los próximos 38 días, de 76 KG, más un stock de seguridad de 2.021916 KG. "
    "El horizonte suma el plazo de entrega, de 31 días (observado en las recepciones del proveedor), y el periodo de "
    "revisión, de 7 días. En total hay 90 KG en tránsito (posición contable de 129 KG), pero solo 45 KG "
    "llegan dentro del horizonte y cuentan para la decisión. " + PROVISIONAL
)


def row(base: dict[str, Any], **changes: Any) -> dict[str, Any]:
    """A deep copy of a fixture with top-level or ``breakdown`` changes (``breakdown__key=value``)."""
    result = copy.deepcopy(base)
    for key, value in changes.items():
        if key.startswith("breakdown__"):
            result["breakdown"][key.removeprefix("breakdown__")] = value
        else:
            result[key] = value
    return result


def context_of(source: dict[str, Any], provenance: dict[str, Any] | None = None):
    from app.genai import build_context

    return build_context(
        recommendation_id=source["recommendation_id"], run_id=source["run_id"], outcome=source["outcome"],
        flags=source["flags"], reasons=source["reasons"], missing_policy_parameters=source["missing_policy_parameters"],
        breakdown=source["breakdown"], unit_of_measure=source["unit_of_measure"],
        provenance=PROVENANCE if provenance is None else provenance,
    )
