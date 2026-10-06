"""Deterministic outputs of an F5c run, the Markdown report and its compact JSON (`DT-073`), SYNTHETIC.

* ``f5c-observations.csv`` — Level 1 observations of every model (F5a format and columns);
* ``f5c-study.csv`` — Level 1 observations of the `DT-011` study (strategy branches, observed and latent truth);
* ``f5c-windows.csv``, ``f5c-orders.csv``, ``f5c-decisions.csv`` — Level 2 per branch (decisions with substitution);
* ``f5c-summary.json`` — metadata, configuration and all aggregates (not versioned);
* the Markdown report and the compact JSON (< 100 KB), versioned in ``docs/reports/``.

``results_sha256`` covers the CSVs and the aggregates, not the run metadata. Nothing recommends or promotes a model.
"""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re

from ..backtest import ALL_SEGMENTS, H1, LR, VIEW_ALL, VIEW_NO_STOCKOUT
from ..candidates import CANDIDATE_NAMES, CANDIDATE_VERSION
from ..report import MODEL_LABELS, _FLAT_LIST, _num, _round
from ..segmentation import SEGMENT_LABELS_ES
from .backtest import ALL_MODELS
from .config import OFFICIAL_BASELINE, STRATEGY_LABELS, STRATEGIES
from .forecaster import split_branch
from .results import PERIOD_FULL
from .run import F5cRun
from .study import TRUTH_LATENT, TRUTH_OBSERVED

OBSERVATIONS_FILE = "f5c-observations.csv"
STUDY_FILE = "f5c-study.csv"
WINDOWS_FILE = "f5c-windows.csv"
ORDERS_FILE = "f5c-orders.csv"
DECISIONS_FILE = "f5c-decisions.csv"
SUMMARY_FILE = "f5c-summary.json"
COMPACT_MAX_BYTES = 100_000

LABELS = dict(MODEL_LABELS)
LABELS.update({
    "ml.holt": "Holt",
    "ml.holt_winters": "Holt-Winters",
    "ml.croston": "Croston",
    "ml.sba": "SBA",
    "ml.tsb": "TSB",
})


def label(branch: str) -> str:
    model, strategy = split_branch(branch)
    base = LABELS.get(model, model)
    return base if strategy == "a" else f"{base} ({strategy})"


def _csv(rows: list[list], header: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def _obs_rows(observations, extra=None) -> list[list]:
    rows = []
    for o in observations:
        rows.append(([extra] if extra is not None else []) + [
            o.as_of, o.product_id, o.location_id, o.model, o.horizon, o.days, o.segment, str(o.stockout).lower(),
            _num(o.forecast), _num(o.actual), _num(o.lower), _num(o.upper), _num(o.error), _num(o.scaled_abs),
            _num(o.scaled_rms),
        ])
    return rows


_OBS_HEADER = ["as_of", "product_id", "location_id", "model", "horizon", "days", "segment", "stockout", "forecast", "actual",
               "lower", "upper", "error", "scaled_abs_error", "scaled_rms_error"]


def detail_csvs(run: F5cRun, results: dict) -> dict[str, str]:
    order = {m: i for i, m in enumerate(ALL_MODELS)}
    obs = sorted(run.level1.observations, key=lambda o: (o.as_of, o.product_id, o.location_id, order[o.model], o.horizon))
    study_rows = []
    for s in sorted(run.study, key=lambda s: (s.as_of, s.key)):
        for kind in (TRUTH_OBSERVED, TRUTH_LATENT):
            study_rows += _obs_rows(s.observations.get(kind, []), kind)
    branches = list(run.sim_config.branches)
    fields = ["days", "demand", "consumption", "units_short", "stockout_days", "stockout_rate", "fill_rate",
              "cycle_service_level", "avg_inventory", "avg_inventory_value", "rotation", "units_ordered", "orders"]
    windows = []
    for (cut, pid, loc, branch), w in sorted(results["level2"]["windows"].items(),
                                             key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], branches.index(kv[0][3]))):
        d = w.as_dict()
        windows.append([cut, pid, loc, branch] + ["" if d[f] is None else (repr(d[f]) if isinstance(d[f], float) else str(d[f])) for f in fields])
    orders, decisions = [], []
    for ps in run.simulation.products:
        for branch in branches:
            trace = ps.traces[branch]
            for o in trace.orders:
                orders.append([branch, ps.key[0], ps.key[1], o.order_id, o.placed_on.isoformat(), str(o.quantity),
                               o.lead_time_days, o.arrival_on.isoformat()])
            for d in trace.decisions:
                decisions.append([branch, ps.key[0], ps.key[1], d.day.isoformat(), d.outcome, "|".join(d.reasons),
                                  d.engine_version, str(d.forecast_available).lower(), d.substitution or ""])
    return {
        OBSERVATIONS_FILE: _csv(_obs_rows(obs), _OBS_HEADER),
        STUDY_FILE: _csv(study_rows, ["truth"] + _OBS_HEADER),
        WINDOWS_FILE: _csv(windows, ["as_of", "product_id", "location_id", "model"] + fields),
        ORDERS_FILE: _csv(orders, ["model", "product_id", "location_id", "order_id", "placed_on", "quantity",
                                   "lead_time_days", "arrival_on"]),
        DECISIONS_FILE: _csv(decisions, ["model", "product_id", "location_id", "day", "outcome", "reasons",
                                         "engine_version", "forecast_available", "substitution"]),
    }


def build_summary(run: F5cRun, results: dict, csvs: dict[str, str], metadata: dict) -> dict:
    public = {k: v for k, v in results.items() if k != "level2"}
    public["level2"] = {k: v for k, v in results["level2"].items() if k != "windows"}
    digest = hashlib.sha256()
    for name in sorted(csvs):
        digest.update(csvs[name].encode("utf-8"))
    digest.update(json.dumps(public, sort_keys=True, default=str).encode("utf-8"))
    metadata = dict(metadata)
    metadata["candidates_version"] = CANDIDATE_VERSION
    return {
        "label": "SYNTHETIC",
        "unit": "F5c (DT-092)",
        "metadata": metadata,
        "config": {"f5c": run.config.describe(), "simulation": run.sim_config.describe()},
        "results": public,
        "files": {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in sorted(csvs.items())},
        "results_sha256": digest.hexdigest(),
    }


#: Field orders of the lists in the compact JSON (lists keep the versioned file under the size budget).
L1_FIELDS = ("cuts", "mean_series", "mase", "rmsse", "wape", "bias_rel", "coverage", "ref_mase", "ref_rmsse", "ref_wape",
             "ref_bias_rel")
L2_FIELDS = ("n_series", "units_short", "stockout_days", "fill_rate", "cycle_service_level", "avg_inventory",
             "relative_inventory", "orders")
COVERAGE_FIELDS = ("current_all_cuts", "current_late_cuts", "calibrated_late_cuts", "n_late", "mean_factor")
STUDY_FIELDS = ("cuts", "n", "mase", "rmsse", "wape", "bias_rel")


def compact_summary(summary: dict) -> dict:
    """Versioned summary: lists with the field orders above, no per-cut detail, Level 2 segments for the nine models."""
    r = summary["results"]
    level1 = {}
    for model, block in r["level1"].items():
        for horizon, views in block.items():
            for view, segs in views.items():
                for segment, e in segs.items():
                    if segment != ALL_SEGMENTS and (horizon != LR or view != VIEW_ALL):
                        continue
                    level1.setdefault(model, {}).setdefault(horizon, {}).setdefault(view, {})[segment] = (
                        [e["cuts"], e["mean_series"]]
                        + [e["model"][m] for m in ("mase", "rmsse", "wape", "bias_rel", "coverage")]
                        + [e["official_baseline"][m] for m in ("mase", "rmsse", "wape", "bias_rel")]
                    )
    l2 = r["level2"]
    aggregates = {}
    for period, block in l2["aggregates"].items():
        segs = {}
        for segment, seg in block["segments"].items():
            rows = {}
            for b, a in seg["branches"].items():
                if segment != ALL_SEGMENTS and b not in ALL_MODELS:
                    continue
                rel = seg["avg_inventory_relative_to_reference"].get(b)
                rows[b] = [a["n_series"], a["units_short"], a["stockout_days"], a["fill_rate"], a["cycle_service_level"],
                           a["avg_inventory"], rel, a["orders"]]
            segs[segment] = rows
        aggregates[period] = {"first": block["first"], "last": block["last"], "segments": segs}
    spearman = {
        name: {h: {m: [s["mean"], s["min"], s["max"], s["n_cuts"]] for m, s in block.items()} for h, block in sets.items()}
        for name, sets in l2["cross"]["model_level_spearman"].items()
    }
    agreement = {
        tol: {h: {m: [a["pairs_compared"], a["pairs_tied"], a["agreement"], a["agreement_with_inventory"]] for m, a in ms.items()}
              for h, ms in block.items()}
        for tol, block in l2["cross"]["series_cut_agreement"].items()
    }
    us = r["us055"]
    coverage = {}
    for model, views in us["models"].items():
        coverage[model] = {"horizons_within_band": views["horizons_within_band"]}
        for view in (VIEW_ALL, VIEW_NO_STOCKOUT):
            coverage[model][view] = {str(h): [block[ALL_SEGMENTS].get(k) for k in COVERAGE_FIELDS] for h, block in views[view].items()}
    study = {}
    for kind, models in r["study"]["metrics"].items():
        for model, horizons in models.items():
            for horizon, views in horizons.items():
                for view, strategies in views.items():
                    study.setdefault(kind, {}).setdefault(model, {}).setdefault(horizon, {})[view] = {
                        st: [e[k] for k in STUDY_FIELDS] for st, e in strategies.items()
                    }
    return _round({
        "label": summary["label"],
        "unit": summary["unit"],
        "metadata": summary["metadata"],
        "config": summary["config"],
        "results_sha256": summary["results_sha256"],
        "files": summary["files"],
        "field_orders": {"level1": list(L1_FIELDS), "level2": list(L2_FIELDS), "coverage": list(COVERAGE_FIELDS),
                         "study": list(STUDY_FIELDS), "spearman": ["mean", "min", "max", "n_cuts"],
                         "agreement": ["pairs_compared", "pairs_tied", "agreement", "agreement_with_inventory"]},
        "results": {
            "top_candidates": r["top_candidates"],
            "eligibility_totals": r["eligibility"]["totals"],
            "level1_pairwise_with_official_baseline": level1,
            "study": {"models": r["study"]["models"], "extreme_series": r["study"]["extreme_series"],
                      "extreme_series_cuts": r["study"]["extreme_series_cuts"], "substitutions": r["study"]["substitutions"],
                      "metrics": study},
            "us055": {"late_cuts": us["late_cuts"], "coverage": coverage},
            "level2": {"branches": l2["branches"], "simulated": l2["simulated"], "excluded": l2["excluded"],
                       "engine_versions": l2["engine_versions"], "aggregates": aggregates,
                       "substitutions": {b: d["substitutions"] for b, d in l2["decisions"].items() if d["substitutions"]},
                       "cross": {"series_cut_agreement": agreement, "model_level_spearman": spearman}},
            "criteria": {n: _compact_entry(e) for n, e in r["criteria"].items()},
            "criteria_meeting_all": r["criteria_meeting_all"],
            "strategy_criteria": {s: {m: _compact_entry(e) for m, e in t.items()} for s, t in r["strategy_criteria"].items()},
            "strategy_meeting_all": r["strategy_meeting_all"],
            "segment_sensitivity": r["segment_sensitivity"],
            "cadence_sensitivity": _compact_cadence(r["cadence_sensitivity"]),
            "parity": {n: p["equal"] for n, p in r["parity"].items()},
        },
    })


def _compact_entry(entry: dict) -> dict:
    return {"statuses": [[row["criterion"], row["status"], bool(row.get("informative"))] for row in entry["rows"]],
            "verdict": entry["verdict"]}


def _compact_cadence(cadence: dict | None) -> dict | None:
    if cadence is None:
        return None
    agg = {p: {b: [a["units_short"], a["stockout_days"], a["fill_rate"], a["avg_inventory"]]
               for b, a in block["segments"][ALL_SEGMENTS]["branches"].items()} for p, block in cadence["aggregates"].items()}
    return {"refit_every_decisions": cadence["refit_every_decisions"], "fields": ["units_short", "stockout_days", "fill_rate", "avg_inventory"],
            "aggregates": agg, "baseline_identical_to_main_run": cadence["baseline_identical_to_main_run"],
            "criteria": {b: [[row["criterion"], row["status"], bool(row.get("informative"))] for row in rows]
                         for b, rows in cadence["level2_criteria"].items()},
            "substitutions": cadence["substitutions"], "sha256": cadence["sha256"]}


def compact_json_text(summary: dict) -> str:
    text = json.dumps(compact_summary(summary), indent=1, sort_keys=True, ensure_ascii=False, default=str)
    text = _FLAT_LIST.sub(lambda m: "[" + re.sub(r",\n\s*", ", ", m.group(1)) + "]", text)
    return text + "\n"


# --- Markdown -------------------------------------------------------------------------------------------------

#: Band label of the Phase 7 recommended by the responsable (review of F5c); applied only by a later F7d change.
BAND_LABEL = ("Intervalo nominal 0,80. Cobertura observada entre 0,75 y 0,85 en pruebas con datos sintéticos; "
              "no validada con datos reales.")
_SHORT = {"CUMPLE": "C", "NO CUMPLE": "**N**", "NO CONCLUYENTE": "NC", "NO EVALUADO": "NE"}
_COLUMNS = ("N1 agregado", "N1 cortes", "N1 segmentos", "Sesgo", "Sesgo por segmento", "N2 faltantes", "N2 *fill rate*",
            "N2 inventario")


def _es_pct(value: float, digits: int) -> str:
    return f"{value * 100:.{digits}f}".replace(".", ",") + " %"


def _verdict_text(v: dict) -> str:
    if v["meets_all"]:
        return "cumple todos los criterios que deciden (sin recomendación ni promoción)."
    parts = []
    if v["failing"]:
        parts.append("no cumple: " + "; ".join(v["failing"]))
    if v["not_conclusive_or_not_evaluated"]:
        parts.append("no concluyente o no evaluado: " + "; ".join(v["not_conclusive_or_not_evaluated"]))
    return " — ".join(parts) + "."


def _strategy_section(r: dict) -> list[str]:
    lines = [
        "## 8. Criterios por estrategia de `DT-011`",
        "",
        "Los mismos criterios para cada modelo estudiado bajo cada estrategia, con la media móvil de 13 semanas **bajo la "
        "misma estrategia** como referencia. Nivel 1 del estudio de `DT-011` (consumo observado, sin las series de desabasto "
        "extremo); Nivel 2 de las ramas «(b)» y «(c)» de §5. C = cumple, **N** = no cumple, NC = no concluyente, NE = no "
        "evaluado. Sin recomendación.",
        "",
        "> **Posible sesgo de selección:** Holt-Winters entró al estudio por su Nivel 1 medido en solo 7 cortes comparables "
        "(semanas 104 a 128), frente a 17 de los demás.",
        "",
        "| Estrategia | Modelo | MASE `L + R` (modelo / media móvil) | Unidades faltantes (modelo / media móvil) | "
        + " | ".join(_COLUMNS) + " | Cumple todo |",
        "|---|---|---|---|" + "---|" * len(_COLUMNS) + "---|",
    ]
    for strategy, table in sorted(r["strategy_criteria"].items()):
        for model, entry in sorted(table.items(), key=lambda kv: ALL_MODELS.index(kv[0])):
            rows = [row for row in entry["rows"] if not row.get("informative")]
            statuses = [_SHORT.get(row["status"], row["status"]) for row in rows]
            if len(statuses) != len(_COLUMNS):
                statuses = (statuses + ["NE"] * len(_COLUMNS))[: len(_COLUMNS)]
            l1 = rows[0]["value"] if rows and isinstance(rows[0]["value"], dict) else {}
            l2 = next((row["value"] for row in rows if row["criterion"].startswith("N2") and "faltantes" in row["criterion"]
                       and isinstance(row["value"], dict)), {})
            lines.append(
                f"| ({strategy}) | {label(model)} | {_f(l1.get('candidate'))} / {_f(l1.get('official_baseline'))} "
                f"| {_f(l2.get('candidate'), 0)} / {_f(l2.get('official_baseline'), 0)} | " + " | ".join(statuses)
                + f" | {'sí' if entry['verdict']['meets_all'] else 'no'} |"
            )
    lines += ["", "Cumplen todos los criterios que deciden, por estrategia: "
              + "; ".join(f"({s}) " + (", ".join(label(m) for m in ms) or "ninguno") for s, ms in r["strategy_meeting_all"].items())
              + ".", ""]
    return lines


def _dt011_conclusion(r: dict) -> list[str]:
    block = r["level2"]["aggregates"][PERIOD_FULL]["segments"][ALL_SEGMENTS]
    branches, relative = block["branches"], block["avg_inventory_relative_to_reference"]
    reductions, inventories = [], []
    for model in r["study"]["models"]:
        base = float(branches[model]["units_short"])
        for strategy in ("b", "c"):
            name = f"{model}@{strategy}"
            if name in branches and base:
                reductions.append(1 - float(branches[name]["units_short"]) / base)
                inventories.append(relative[name] - 1)
    if not reductions:
        return []
    return [
        "**Conclusión provisional del estudio** (revisión del responsable, 2026-10-06; solo con datos `SYNTHETIC`): las "
        f"estrategias (b) y (c) reducen las unidades faltantes entre un {_es_pct(min(reductions), 0)} y un {_es_pct(max(reductions), 0)} "
        f"en los modelos estudiados, con un inventario medio entre un {_es_pct(min(inventories), 1)} y un {_es_pct(max(inventories), 1)} "
        "mayor que el de "
        "la media móvil 13 con (a). Adoptar una en producción exige una unidad propia que cambie U3 y una DT nueva.",
        "",
        "**PROPUESTA del desarrollador** (pendiente de decisión del responsable): preferir (b). La diferencia con (c) está "
        "dentro del ruido, (b) no necesita un estimador con parámetros propios y la API ya expone `days_observed` y "
        "`stockout_days` por periodo.",
        "",
    ]


def _sensitivity_section(r: dict, md: dict) -> list[str]:
    lines = ["## 10. Sensibilidades", ""]
    cad = r.get("cadence_sensitivity")
    if cad:
        block = cad["aggregates"][PERIOD_FULL]["segments"][ALL_SEGMENTS]
        lines += [
            "### Cadencia de reoptimización",
            "",
            "Los candidatos reoptimizan cada 4 decisiones (`DT-093` punto 9). Aquí, Holt, Croston y TSB reoptimizan en cada "
            "decisión semanal, con la media móvil 13 en la misma simulación. Se calcula en el mismo comando de §1 (etapa "
            f"«cadence»); huella del detalle: `{cad['sha256']}`. Media móvil idéntica a la de §5: "
            f"{'sí' if cad['baseline_identical_to_main_run'] else 'no'}.",
            "",
            "| Rama | Unidades faltantes | Relativo a media móvil | *Fill rate* | Inventario relativo | N2 faltantes | N2 *fill rate* | N2 inventario |",
            "|---|---|---|---|---|---|---|---|",
        ]
        base = float(block["branches"][OFFICIAL_BASELINE]["units_short"])
        for b, a in block["branches"].items():
            statuses = [row["status"] for row in cad["level2_criteria"].get(b, []) if not row.get("informative")]
            statuses = statuses or ["—", "—", "—"]
            lines.append(
                f"| {label(b)} | {_f(a['units_short'], 0)} | {_pct(float(a['units_short']) / base - 1)} | {_f(a['fill_rate'], 4)} "
                f"| {_f(block['avg_inventory_relative_to_reference'].get(b))} | " + " | ".join(statuses) + " |"
            )
        meeting = [b for b, rows in cad["level2_criteria"].items()
                   if all(row["status"] == "CUMPLE" for row in rows if not row.get("informative"))]
        lines += ["", "Con reoptimización semanal cumplen los criterios de Nivel 2: "
                  + (", ".join(label(b) for b in meeting) or "ninguno") + ".", ""]
    seg = r["segment_sensitivity"]
    lines += [
        "### Tamaño mínimo de segmento",
        "",
        "El segmento intermitente tiene en promedio 10 series por corte, justo en el umbral de `DT-091`. Cambios respecto al "
        "umbral de 10, sobre las tablas de §7 y §8:",
        "",
        "| Umbral | Resultados que cambian | Veredictos que cambian |",
        "|---|---|---|",
    ]
    def where(strategy: str, model: str) -> str:
        return f"{label(model)} ({'§7' if strategy == 'a*' else '§8, (' + strategy + ')'})"

    for threshold, s in seg.items():
        changes = [f"{where(st, m)}: {'cumple todo' if new else 'no cumple todo'} (antes: {'cumple todo' if old else 'no cumple todo'})"
                   for st, m, old, new in s["verdict_changes"]]
        lines.append(f"| {threshold} | {len(s['status_changes'])} de {s['compared']} | " + ("; ".join(changes) or "ninguno") + " |")
    for threshold, s in seg.items():
        if s["status_changes"]:
            lines += ["", f"Con {threshold}: " + "; ".join(f"{where(st, m)}, «{c}»: {old} → {new}" for st, m, c, old, new in s["status_changes"]) + "."]
    lines.append("")
    return lines



def _f(v: object, digits: int = 3) -> str:
    if v is None:
        return "—"
    if isinstance(v, str):
        try:
            v = float(v)
        except ValueError:
            return v
    return f"{v:,.{digits}f}"


def _pct(v: object) -> str:
    return "—" if v is None else f"{v:+.1%}"


def _seg(segment: str) -> str:
    return "todos" if segment == ALL_SEGMENTS else SEGMENT_LABELS_ES.get(segment, segment)


def _value_text(value: object) -> str:
    if isinstance(value, dict):
        return "; ".join(f"{k}: {_f(v) if isinstance(v, float) else v}" for k, v in value.items())
    if isinstance(value, list):
        parts = []
        for item in value:
            if item.get("blocks"):
                change = item.get("relative_change", item.get("abs_worsening"))
                parts.append(f"{_seg(item['segment'])}: {_f(change)}")
        return "; ".join(parts) or "ningún segmento bloquea"
    return str(value)


def render_markdown(summary: dict) -> str:
    md, r = summary["metadata"], summary["results"]
    cfg = summary["config"]["f5c"]
    l2 = r["level2"]
    order = {b: i for i, b in enumerate(l2["branches"])}
    lines = [
        "# Fase 5 — F5c: modelos candidatos, estudio de `DT-011` e intervalos (US-055)",
        "",
        "> **SYNTHETIC.** Todo se calcula con el dataset sintético. Los 17 cortes de `DT-075` y el simulador de F5b; el",
        "> *holdout* no se lee. **No recomienda ni promueve ningún modelo** (`DT-084`): la tabla de criterios es",
        "> automática e informativa. Las conclusiones que usan la demanda latente solo valen para datos `SYNTHETIC`.",
        "> Generado por `python -m ml candidates`; no editar a mano.",
        "",
        "## 1. Ejecución",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Fecha | {md.get('generated_on', '—')} |",
        f"| Comando | `{md.get('command') or '—'}` |",
        f"| Dataset | `{md['dataset_version']}` ({md['data_origin']}) |",
        f"| Código | `ml` {md['ml_version']}; candidatos {md['candidates_version']} |",
        f"| Motor U1 | {md['engine_version_u1']}; versiones vistas en las decisiones: {', '.join(l2['engine_versions'])} |",
        f"| Commit | `{md['git_commit']}` (cambios sin commit en archivos versionados: {md['git_tracked_changes']}) |",
        f"| Python | {md['python_version']} |",
        f"| Aleatoriedad | {md['seeds']} |",
        f"| `results_sha256` | `{summary['results_sha256']}` |",
        "",
        "## 2. Criterios y valores provisionales",
        "",
        "Criterios del responsable (`DT-091`, `DT-093`, `ACEPTADA`, provisionales):",
        "",
    ]
    for k, v in cfg["criteria"].items():
        lines.append(f"- {k}: {v}")
    lines += [
        "",
        "Valores provisionales de esta unidad (`PROPUESTA`, configurables):",
        "",
        "- Candidatos: rejillas y arranques en la configuración del JSON (`candidates`); mínimo de 25 semanas (104 para "
        "Holt-Winters); intervalo nearest-rank 10/90 de los errores dentro de muestra, como el SES de F5a.",
        "- Comparación por pares con el baseline oficial (media móvil 13): un corte es comparable si ambos tienen observación "
        "con dato real completo; agregado = media de las métricas por corte; un segmento bloquea si tiene en promedio ≥ 10 "
        "series por corte comparable; el sesgo se compara en valor absoluto.",
        "- Nivel 2: los criterios se aplican al periodo completo; el periodo sin calentamiento se informa al lado.",
        "- SES y los baselines conservan la cadencia de F5b (pronóstico recalculado en cada decisión), para que sus "
        "resultados no cambien; los candidatos reoptimizan cada 4 decisiones (`DT-093` punto 9).",
        f"- US-055: cortes tardíos {', '.join(r['us055']['late_cuts'])}; calibración por factor de ensanche con los cortes "
        "cuya ventana de evaluación termina antes del corte medido.",
        f"- `DT-011`: modelos estudiados {', '.join(label(m) for m in r['study']['models'])} (los dos mejores candidatos por "
        "Nivel 1: menor MASE en `L + R` relativo al baseline oficial).",
        "",
        "## 3. Elegibilidad y sustituciones",
        "",
        "| Candidato | Pronósticos propios | No elegible | Sustituido por el baseline oficial (valor inválido) |",
        "|---|---|---|---|",
    ]
    for name in CANDIDATE_NAMES:
        t = r["eligibility"]["totals"][name]
        lines.append(f"| {label(name)} | {t['OK']} | {t['NOT_ELIGIBLE']} | {t['SUBSTITUTED']} |")
    lines += [
        "",
        "Holt-Winters solo es elegible con 104 semanas de entrenamiento: cortes de las semanas 104 a 128. Una sustitución "
        "ocurre cuando un valor no cruza la frontera de `DT-074` (sobre todo, pronósticos negativos de Holt y Holt-Winters "
        "en series con tendencia descendente); la serie usa entonces el baseline oficial y cuenta como observación del "
        "candidato.",
        "",
        "## 4. Nivel 1 frente al baseline oficial (SYNTHETIC)",
        "",
        "Media de las métricas por corte en el conjunto común de cada par (modelo, media móvil 13). MASE en `L + R` es la "
        "métrica primaria (`DT-090`, `DT-093`); `h = 1` es secundaria.",
        "",
        "| Modelo | Horizonte | Vista | Cortes | Series por corte | MASE | MASE media móvil | Relativo | RMSSE | WAPE | Sesgo relativo | Cobertura (semana 1) |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for model in ALL_MODELS:
        block = r["level1"][model]
        for horizon in (LR, H1):
            for view in (VIEW_ALL, VIEW_NO_STOCKOUT):
                e = block[horizon][view].get(ALL_SEGMENTS)
                if not e:
                    continue
                m, b = e["model"], e["official_baseline"]
                rel = m["mase"] / b["mase"] - 1 if m["mase"] is not None and b["mase"] else None
                lines.append(
                    f"| {label(model)} | {'L + R' if horizon == LR else 'h = 1'} | {'todas' if view == VIEW_ALL else 'sin desabasto'} "
                    f"| {e['cuts']} | {_f(e['mean_series'], 1)} | {_f(m['mase'])} | {_f(b['mase'])} | {_pct(rel)} | {_f(m['rmsse'])} "
                    f"| {_f(m['wape'])} | {_f(m['bias_rel'])} | {_f(m['coverage'])} |"
                )
    lines += [
        "",
        "Por segmento (MASE en `L + R`, todas las semanas; relativo a la media móvil en el mismo conjunto):",
        "",
        "| Modelo | Segmento | Cortes | Series por corte | MASE | MASE media móvil | Relativo | Sesgo relativo |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for model in ALL_MODELS:
        if model == OFFICIAL_BASELINE:
            continue
        for segment, e in r["level1"][model][LR][VIEW_ALL].items():
            if segment == ALL_SEGMENTS:
                continue
            m, b = e["model"], e["official_baseline"]
            rel = m["mase"] / b["mase"] - 1 if m["mase"] is not None and b["mase"] else None
            lines.append(f"| {label(model)} | {_seg(segment)} | {e['cuts']} | {_f(e['mean_series'], 1)} | {_f(m['mase'])} "
                         f"| {_f(b['mase'])} | {_pct(rel)} | {_f(m['bias_rel'])} |")
    lines += ["", "## 5. Nivel 2 por rama, segmento y periodo (SYNTHETIC)", ""]
    lines.append(f"Series simuladas: {l2['simulated']}. Misma `engine_version` en todas las ramas. Las ramas «(b)» y «(c)» "
                 "son las estrategias de `DT-011` (§8).")
    lines.append("")
    for period, block in l2["aggregates"].items():
        lines += [
            f"### {'Periodo completo' if period == PERIOD_FULL else 'Sin las semanas de calentamiento'} ({block['first']} a {block['last']})",
            "",
            "| Segmento | Rama | Series | Unidades faltantes | Días con desabasto | *Fill rate* | Servicio por ciclos | Inventario medio | Relativo a media móvil | Órdenes |",
            "|---|---|---|---|---|---|---|---|---|---|",
        ]
        for segment, seg in block["segments"].items():
            for branch, a in sorted(seg["branches"].items(), key=lambda kv: order[kv[0]]):
                if segment != ALL_SEGMENTS and branch not in ALL_MODELS:
                    continue
                lines.append(
                    f"| {_seg(segment)} | {label(branch)} | {a['n_series']} | {_f(a['units_short'], 0)} | {a['stockout_days']} "
                    f"| {_f(a['fill_rate'], 4)} | {_f(a['cycle_service_level'], 4)} | {_f(a['avg_inventory'], 1)} "
                    f"| {_f(seg['avg_inventory_relative_to_reference'].get(branch))} | {a['orders']} |"
                )
        lines.append("")
    lines += ["Sustituciones por el baseline oficial en las decisiones del simulador (`DT-093` punto 11):", "",
              "| Rama | No elegible | Valor inválido |", "|---|---|---|"]
    for branch, d in sorted(l2["decisions"].items(), key=lambda kv: order[kv[0]]):
        s = d["substitutions"]
        if s:
            lines.append(f"| {label(branch)} | {s.get('NOT_ELIGIBLE', 0)} | {s.get('INVALID', 0)} |")
    lines += [
        "",
        "## 6. Cruce informativo con el Nivel 1 (`DT-078`)",
        "",
        "Acuerdo por serie y corte entre la métrica de Nivel 1 y las unidades faltantes de la ventana, sobre los nueve "
        "modelos; «con inventario»: la rama preferida no supera el inventario medio de la otra más allá de la tolerancia.",
        "",
        "| Tolerancia | Horizonte | Métrica | Pares | Empates | Acuerdo | Acuerdo con restricción de inventario |",
        "|---|---|---|---|---|---|---|",
    ]
    for tol, block in l2["cross"]["series_cut_agreement"].items():
        for horizon, metrics in block.items():
            for metric, a in metrics.items():
                lines.append(f"| {float(tol):.0%} | {'L + R' if horizon == LR else 'h = 1'} | {metric.upper()} | {a['pairs_compared']} "
                             f"| {a['pairs_tied']} | {_f(a['agreement'])} | {_f(a['agreement_with_inventory'])} |")
    lines += ["", "Spearman entre modelos por corte (métrica agregada frente a unidades faltantes):", "",
              "| Conjunto | Horizonte | Métrica | ρ medio | mín | máx | Cortes |", "|---|---|---|---|---|---|---|"]
    for name, sets in l2["cross"]["model_level_spearman"].items():
        for horizon, metrics in sets.items():
            for metric, s in metrics.items():
                lines.append(f"| {'sin Holt-Winters' if name == 'without_holt_winters' else 'los nueve'} | "
                             f"{'L + R' if horizon == LR else 'h = 1'} | {metric.upper()} | {_f(s['mean'])} | {_f(s['min'])} "
                             f"| {_f(s['max'])} | {s['n_cuts']} |")
    lines += [
        "",
        "## 7. Criterios por modelo (cumple / no cumple, sin recomendación)",
        "",
        "Automático, frente a la media móvil de 13 semanas con la estrategia (a). Incluye SES, el candidato más fuerte de "
        "`DT-089`. «Informativo»: periodo sin calentamiento, no decide.",
        "",
        "**Cumplen todos los criterios que deciden:** " + (", ".join(label(m) for m in r["criteria_meeting_all"]) or "ninguno")
        + ". Es un hecho del cálculo, no una recomendación: sin G2 ni G3 no se promueve nada (`DT-084`).",
        "",
    ]
    for name, entry in sorted(r["criteria"].items(), key=lambda kv: ALL_MODELS.index(kv[0])):
        lines += [f"### {label(name)}", "", "| Criterio | Valor | Umbral | Resultado |", "|---|---|---|---|"]
        for row in entry["rows"]:
            crit = row["criterion"] + (" (informativo)" if row.get("informative") else "")
            lines.append(f"| {crit} | {_value_text(row['value'])} | {row['threshold']} | {row['status']} |")
        lines += ["", "Veredicto: " + _verdict_text(entry["verdict"]), ""]
    lines += _strategy_section(r)
    st = r["study"]
    lines += [
        "## 9. Estudio de `DT-011` (desabasto)",
        "",
        "Estrategias de entrenamiento: " + "; ".join(STRATEGY_LABELS[s] for s in STRATEGIES) + ". La verdad nunca es un valor "
        "imputado. Conjunto común de las tres estrategias de cada modelo; series con más del 50 % de días con desabasto "
        f"aparte: {len(st['extreme_series'])} series ({st['extreme_series_cuts']} serie-cortes). "
        "**La comparación contra la demanda latente solo es posible con datos `SYNTHETIC`.**",
        "",
        "| Verdad | Modelo | Horizonte | Vista | Estrategia | Cortes | MASE | WAPE | Sesgo relativo |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for kind in (TRUTH_OBSERVED, TRUTH_LATENT):
        for model in st["models"]:
            for horizon in (LR, H1):
                for view in (VIEW_ALL, VIEW_NO_STOCKOUT):
                    entry = st["metrics"].get(kind, {}).get(model, {}).get(horizon, {}).get(view)
                    if not entry:
                        continue
                    for strategy in STRATEGIES:
                        e = entry[strategy]
                        lines.append(
                            f"| {'consumo observado' if kind == TRUTH_OBSERVED else 'demanda latente'} | {label(model)} "
                            f"| {'L + R' if horizon == LR else 'h = 1'} | {'todas' if view == VIEW_ALL else 'sin desabasto'} "
                            f"| ({strategy}) | {e['cuts']} | {_f(e['mase'])} | {_f(e['wape'])} | {_f(e['bias_rel'])} |"
                        )
    if st["substitutions"]:
        lines += ["", "Sustituciones en el estudio: " + ", ".join(f"{label(k)}: {v}" for k, v in st["substitutions"].items()) + "."]
    lines += ["", "Nivel 2 de las estrategias: filas «(b)» y «(c)» de §5 (población completa).", ""]
    lines += _dt011_conclusion(r)
    lines += _sensitivity_section(r, md)
    us = r["us055"]["models"]
    lines += [
        "## 11. US-055: cobertura de los intervalos",
        "",
        "Cobertura semanal (nominal 0,80) contra el consumo observado. Calibrado si la cobertura en los cortes tardíos está "
        "entre 0,75 y 0,85 en el horizonte (`DT-093` punto 6). Solo decide el rótulo de la banda.",
        "",
        "| Modelo | Horizontes en banda: actual | Horizontes en banda: calibrado | Cobertura actual, todos los cortes (h = 1 / h = 14) | Actual, tardíos (h = 1 / h = 14) | Calibrado, tardíos (h = 1 / h = 14) |",
        "|---|---|---|---|---|---|",
    ]
    for model in ALL_MODELS:
        c = us.get(model)
        if not c:
            continue
        w = c["horizons_within_band"]
        a1 = c[VIEW_ALL]["1"][ALL_SEGMENTS]
        a14 = c[VIEW_ALL]["14"][ALL_SEGMENTS]
        lines.append(
            f"| {label(model)} | {w['current_late_cuts']} de {w['of']} | {w['calibrated_late_cuts']} de {w['of']} "
            f"| {_f(a1.get('current_all_cuts'))} / {_f(a14.get('current_all_cuts'))} | {_f(a1.get('current_late_cuts'))} / "
            f"{_f(a14.get('current_late_cuts'))} | {_f(a1.get('calibrated_late_cuts'))} / {_f(a14.get('calibrated_late_cuts'))} |"
        )
    official = us.get(OFFICIAL_BASELINE, {})
    within = official.get("horizons_within_band", {})
    if within:
        n, of = within["current_late_cuts"], within["of"]
        detail = (f"El intervalo actual de U3 queda en banda en {n} de {of} horizontes con todas las semanas y en "
                  f"{within['current_late_cuts_no_stockout']} de {of} sin las semanas con desabasto; la variante calibrada, en "
                  f"{within['calibrated_late_cuts']} de {of}.")
        if n == of:
            lines += ["", "**Rótulo recomendado para la banda de la Fase 7** (media móvil 13, la que sirve U3; texto del "
                      "responsable): **«" + BAND_LABEL + "»** " + detail + " No hace falta calibrarlo con estos datos. "
                      "Es un ajuste posterior de F7d que se autoriza aparte: la Fase 7 no se modifica."]
        else:
            lines += ["", "**Rótulo recomendado para la banda de la Fase 7** (media móvil 13, la que sirve U3): "
                      "**«nominal 0,80, no validada»**. " + detail + " Adoptar una calibración exigiría cambiar U3 y F7d, "
                      "fuera de F5c: la Fase 7 no se modifica."]
    lines += ["", "## 12. Paridad con F5a y F5b", "",
              "Huellas de los archivos de detalle de F5a y F5b recalculados desde F5c (sus cuatro modelos):", "",
              "| Archivo | F5c | Registrado | Igual |", "|---|---|---|---|"]
    for name, p in r["parity"].items():
        lines.append(f"| `{name}` | `{p['f5c'][:16]}…` | `{(p['recorded'] or '—')[:16]}…` | {p['equal']} |")
    lines += [
        "",
        "## 13. Salidas",
        "",
        "Junto a este informe se versiona un JSON resumido (mismo nombre, `.json`). El detalle se regenera de forma "
        "determinista con el comando de §1 en `ml/out/`, ignorado por Git. Huellas:",
        "",
    ]
    for name, sha in summary["files"].items():
        lines.append(f"- `{name}`: `{sha}`")
    lines.append("")
    return "\n".join(lines)
