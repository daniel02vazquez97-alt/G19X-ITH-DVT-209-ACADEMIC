"""Automatic table of the acceptance criteria per candidate (`DT-079` point 1, `DT-091`, `DT-093`), SYNTHETIC.

Each row is CUMPLE / NO CUMPLE / NO CONCLUYENTE with its values. The table **does not recommend or promote
anything** (`DT-084`): promotion needs G2 and G3, which are not authorised.

Interpretations of this unit (PROPUESTA, provisional, reported):

* the comparison is pairwise, candidate against the official baseline: a cut is comparable when both models have
  an observation with complete observed truth for at least one series (`DT-093` point 3);
* the Level 1 aggregate is the mean over the comparable cuts of the per-cut metric on the pairwise common set;
* a segment blocks when it has, on average over the comparable cuts, at least 10 series (`DT-091` point 1);
* the bias criterion compares absolute relative biases (``|bias_rel|``);
* Level 2 uses the full simulated period; the period without warm-up is reported alongside.
"""

from __future__ import annotations

import math
from collections import defaultdict
from collections.abc import Sequence

from ..backtest import ALL_SEGMENTS, LR, VIEW_ALL, VIEW_NO_STOCKOUT
from ..metrics import Observation, aggregate
from .config import OFFICIAL_BASELINE, Criteria

CUMPLE = "CUMPLE"
NO_CUMPLE = "NO CUMPLE"
NO_CONCLUYENTE = "NO CONCLUYENTE"


def _status(ok: bool) -> str:
    return CUMPLE if ok else NO_CUMPLE


def pairwise_per_cut(
    observations: Sequence[Observation], model: str, reference: str, horizon: str, view: str = VIEW_ALL
) -> dict[str, dict[str, dict]]:
    """``cut → segment → {"model": aggregate, "reference": aggregate, "n": series}`` on the pairwise common set."""
    by_key: dict[tuple, dict[str, Observation]] = defaultdict(dict)
    for o in observations:
        if o.horizon != horizon or o.model not in (model, reference):
            continue
        if view == VIEW_NO_STOCKOUT and o.stockout:
            continue
        by_key[(o.as_of, o.product_id, o.location_id)][o.model] = o
    grouped: dict[tuple[str, str], dict[str, list[Observation]]] = defaultdict(lambda: defaultdict(list))
    for (cut, _p, _l), pair in by_key.items():
        if model not in pair or reference not in pair:
            continue
        for segment in (ALL_SEGMENTS, pair[model].segment):
            grouped[(cut, segment)][model].append(pair[model])
            if reference != model:
                grouped[(cut, segment)][reference].append(pair[reference])
    out: dict[str, dict[str, dict]] = defaultdict(dict)
    for (cut, segment), lists in sorted(grouped.items()):
        out[cut][segment] = {
            "model": aggregate(lists[model]),
            "reference": aggregate(lists[reference] if reference != model else lists[model]),
            "n": len(lists[model]),
        }
    return dict(out)


def _mean(values: Sequence[float]) -> float | None:
    present = [v for v in values if v is not None]
    return math.fsum(present) / len(present) if present else None


def relative_level1(observations: Sequence[Observation], model: str, metric: str = "mase", horizon: str = LR) -> float | None:
    """Mean per-cut metric of ``model`` ÷ that of the official baseline on their pairwise comparable cuts."""
    per_cut = pairwise_per_cut(observations, model, OFFICIAL_BASELINE, horizon)
    m = _mean([c[ALL_SEGMENTS]["model"][metric] for c in per_cut.values() if ALL_SEGMENTS in c])
    r = _mean([c[ALL_SEGMENTS]["reference"][metric] for c in per_cut.values() if ALL_SEGMENTS in c])
    return m / r if m is not None and r else None


def level1_rows(observations: Sequence[Observation], candidate: str, crit: Criteria) -> list[dict]:
    metric, horizon = crit.primary_metric, crit.primary_horizon
    per_cut = pairwise_per_cut(observations, candidate, OFFICIAL_BASELINE, horizon)
    cuts = sorted(c for c, segs in per_cut.items() if ALL_SEGMENTS in segs and segs[ALL_SEGMENTS]["model"][metric] is not None)
    n = len(cuts)
    rows: list[dict] = []
    conclusive = n >= crit.min_comparable_cuts
    cand = [per_cut[c][ALL_SEGMENTS]["model"][metric] for c in cuts]
    ref = [per_cut[c][ALL_SEGMENTS]["reference"][metric] for c in cuts]
    m, r = _mean(cand), _mean(ref)
    rows.append({
        "criterion": "N1: mejora agregada de MASE en L + R",
        "value": {"candidate": m, "official_baseline": r, "comparable_cuts": n},
        "threshold": "candidato < baseline oficial",
        "status": _status(m is not None and r is not None and m < r) if conclusive else NO_CONCLUYENTE,
    })
    improved = sum(1 for a, b in zip(cand, ref) if a < b)
    needed = math.ceil(n * crit.cuts_fraction_num / crit.cuts_fraction_den)
    rows.append({
        "criterion": "N1: mejora en ⌈2/3⌉ de los cortes comparables (mínimo 5)",
        "value": {"improved": improved, "needed": needed, "comparable_cuts": n},
        "threshold": f"≥ {needed} de {n}",
        "status": _status(improved >= needed) if conclusive else NO_CONCLUYENTE,
    })
    seg_n: dict[str, list[int]] = defaultdict(list)
    seg_m: dict[str, list[float]] = defaultdict(list)
    seg_r: dict[str, list[float]] = defaultdict(list)
    seg_bm: dict[str, list[float]] = defaultdict(list)
    seg_br: dict[str, list[float]] = defaultdict(list)
    for c in cuts:
        for segment, block in per_cut[c].items():
            if segment == ALL_SEGMENTS:
                continue
            seg_n[segment].append(block["n"])
            seg_m[segment].append(block["model"][metric])
            seg_r[segment].append(block["reference"][metric])
            seg_bm[segment].append(block["model"]["bias_rel"])
            seg_br[segment].append(block["reference"]["bias_rel"])
    worst = []
    blocking_fail = False
    for segment in sorted(seg_n):
        size = math.fsum(seg_n[segment]) / n if n else 0.0
        sm, sr = _mean(seg_m[segment]), _mean(seg_r[segment])
        change = (sm - sr) / sr if sm is not None and sr else None
        blocks = size >= crit.segment_min_products
        fails = blocks and change is not None and change > crit.segment_worsening
        blocking_fail = blocking_fail or fails
        worst.append({"segment": segment, "mean_series": size, "blocks": blocks, "relative_change": change})
    rows.append({
        "criterion": "N1: ningún segmento de ≥ 10 productos empeora más de un 5 % en MASE",
        "value": worst,
        "threshold": f"cambio relativo ≤ {crit.segment_worsening:.0%} en segmentos que bloquean",
        "status": _status(not blocking_fail) if conclusive else NO_CONCLUYENTE,
    })
    bias_c = _mean([per_cut[c][ALL_SEGMENTS]["model"]["bias_rel"] for c in cuts])
    rows.append({
        "criterion": "Sesgo relativo medio en L + R dentro de ±0,10",
        "value": {"candidate": bias_c, "official_baseline": _mean([per_cut[c][ALL_SEGMENTS]["reference"]["bias_rel"] for c in cuts])},
        "threshold": f"valor absoluto ≤ {crit.bias_band}",
        "status": _status(bias_c is not None and abs(bias_c) <= crit.bias_band) if conclusive else NO_CONCLUYENTE,
    })
    seg_bias = []
    bias_fail = False
    for item in worst:
        segment = item["segment"]
        bm, br = _mean(seg_bm[segment]), _mean(seg_br[segment])
        delta = abs(bm) - abs(br) if bm is not None and br is not None else None
        fails = item["blocks"] and delta is not None and delta > crit.segment_bias_worsening
        bias_fail = bias_fail or fails
        seg_bias.append({"segment": segment, "blocks": item["blocks"], "candidate": bm, "official_baseline": br, "abs_worsening": delta})
    rows.append({
        "criterion": "Sesgo por segmento de ≥ 10 productos no peor en más de 0,05",
        "value": seg_bias,
        "threshold": f"aumento del valor absoluto del sesgo ≤ {crit.segment_bias_worsening}",
        "status": _status(not bias_fail) if conclusive else NO_CONCLUYENTE,
    })
    return rows


def level2_rows(aggregates: dict, candidate: str, crit: Criteria, period: str) -> list[dict]:
    block = aggregates.get(period, {}).get("segments", {}).get(ALL_SEGMENTS, {}).get("branches", {})
    if candidate not in block or OFFICIAL_BASELINE not in block:
        return [{"criterion": f"N2 ({period})", "value": None, "threshold": "—", "status": NO_CONCLUYENTE}]
    c, b = block[candidate], block[OFFICIAL_BASELINE]
    cs, bs = float(c["units_short"]), float(b["units_short"])
    return [
        {
            "criterion": f"N2 ({period}): unidades faltantes no peores en más de un 2 %",
            "value": {"candidate": cs, "official_baseline": bs, "relative": (cs - bs) / bs if bs else None},
            "threshold": f"≤ {bs * (1 + crit.units_short_tolerance):,.1f}",
            "status": _status(cs <= bs * (1 + crit.units_short_tolerance)),
        },
        {
            "criterion": f"N2 ({period}): fill rate no peor en más de 0,2 puntos",
            "value": {"candidate": c["fill_rate"], "official_baseline": b["fill_rate"]},
            "threshold": f"≥ {b['fill_rate'] - crit.fill_rate_points:.4f}",
            "status": _status(c["fill_rate"] >= b["fill_rate"] - crit.fill_rate_points),
        },
        {
            "criterion": f"N2 ({period}): inventario medio como máximo +5 %",
            "value": {"candidate": c["avg_inventory"], "official_baseline": b["avg_inventory"],
                      "relative": c["avg_inventory"] / b["avg_inventory"] if b["avg_inventory"] else None},
            "threshold": f"≤ {1 + crit.inventory_tolerance:.2f} × baseline",
            "status": _status(c["avg_inventory"] <= b["avg_inventory"] * (1 + crit.inventory_tolerance)),
        },
    ]
