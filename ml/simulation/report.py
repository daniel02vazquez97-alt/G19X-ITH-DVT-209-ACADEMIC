"""Deterministic outputs of an F5b run, the Markdown report and its compact JSON (`DT-073`).

* ``f5b-windows.csv`` — branch × product × 14-week window of each F5a cut (same keys as
  ``f5a-observations.csv``): Level 2 metrics of the window;
* ``f5b-orders.csv`` and ``f5b-decisions.csv`` — every simulated order and every weekly decision;
* ``f5b-summary.json`` — run metadata, configuration and all the aggregates (not versioned);
* the Markdown report and the compact JSON (< 50 KB), both versioned in ``docs/reports/``.

``results_sha256`` covers the three CSVs and the aggregates (not the run metadata).
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import io
import json
import re
import statistics
from collections import Counter, defaultdict

from app.forecasting import REFERENCE

from ..backtest import ALL_SEGMENTS, HORIZONS, BacktestResult
from ..cuts import development_cuts
from ..models import MODEL_NAMES
from ..report import MODEL_LABELS, _FLAT_LIST, _round
from ..segmentation import SEGMENT_LABELS_ES, SEGMENTS
from .level2 import (
    WindowMetrics,
    identical_series_cut_ordering,
    model_level_spearman,
    pooled,
    relative_inventory,
    series_cut_agreement,
    window_metrics,
)
from .simulator import SimConfig, SimulationInputs, SimulationResult

WINDOWS_FILE = "f5b-windows.csv"
ORDERS_FILE = "f5b-orders.csv"
DECISIONS_FILE = "f5b-decisions.csv"
SUMMARY_FILE = "f5b-summary.json"
COMPACT_MAX_BYTES = 50_000
PERIOD_FULL = "FULL"
PERIOD_NO_WARMUP = "NO_WARMUP"
_ONE_DAY = _dt.timedelta(days=1)
_WINDOW_DAYS = 98


def _segments_at_first_cut(level1: BacktestResult, first_cut: _dt.date) -> dict[tuple[int, int], str]:
    return {sc.key: sc.segment or "" for sc in level1.series_cuts if sc.as_of == first_cut}


def build_results(inputs: SimulationInputs, result: SimulationResult, level1: BacktestResult) -> dict:
    """All the aggregates of the run, plus the per-window metrics used by the CSVs."""
    config = result.config
    segments = _segments_at_first_cut(level1, config.first_cut)
    branches = config.branches
    cuts = [c for c in development_cuts() if c >= config.first_cut and c + _ONE_DAY * _WINDOW_DAYS <= config.period_end]
    windows: dict[tuple[str, int, int, str], WindowMetrics] = {}
    for ps in result.products:
        cost = inputs.unit_costs.get(ps.key[0])
        for cut in cuts:
            for branch in branches:
                windows[(cut.isoformat(), ps.key[0], ps.key[1], branch)] = window_metrics(
                    ps, branch, cut + _ONE_DAY, cut + _ONE_DAY * _WINDOW_DAYS, cost
                )
    periods = {
        PERIOD_FULL: (config.first_cut + _ONE_DAY, config.period_end),
        PERIOD_NO_WARMUP: (config.first_cut + _ONE_DAY * (7 * config.warmup_weeks + 1), config.period_end),
    }
    aggregates: dict = {}
    for period, (first, last) in periods.items():
        if first > last:
            continue  # period shorter than the warm-up
        per_branch: dict[str, dict[str, list[WindowMetrics]]] = defaultdict(lambda: defaultdict(list))
        for ps in result.products:
            cost = inputs.unit_costs.get(ps.key[0])
            segment = segments.get(ps.key, "")
            for branch in branches:
                w = window_metrics(ps, branch, first, last, cost)
                per_branch[branch][ALL_SEGMENTS].append(w)
                per_branch[branch][segment].append(w)
        block: dict = {"first": first.isoformat(), "last": last.isoformat(), "segments": {}}
        for segment in (ALL_SEGMENTS,) + SEGMENTS:
            by_branch = {b: pooled(per_branch[b][segment]) for b in branches if per_branch[b].get(segment)}
            if not by_branch:
                continue
            block["segments"][segment] = {
                "branches": by_branch,
                "avg_inventory_relative_to_reference": relative_inventory(by_branch, REFERENCE.name),
            }
        aggregates[period] = block
    across_cuts: dict = {}
    for branch in branches:
        per_cut = defaultdict(list)
        for (cut, _pid, _loc, b), w in windows.items():
            if b == branch:
                per_cut[cut].append(w)
        stats = {}
        for field in ("units_short", "fill_rate", "stockout_rate", "avg_inventory"):
            values = []
            for cut in sorted(per_cut):
                v = pooled(per_cut[cut])[field]
                if v is not None:
                    values.append(float(v))
            stats[field] = {
                "mean": statistics.fmean(values) if values else None,
                "sd": statistics.pstdev(values) if len(values) > 1 else 0.0,
                "min": min(values) if values else None,
                "max": max(values) if values else None,
                "n_cuts": len(values),
            }
        across_cuts[branch] = stats
    simulated = {ps.key for ps in result.products}
    observations = [o for o in level1.observations if (o.product_id, o.location_id) in simulated]
    cut_labels = [c.isoformat() for c in cuts]
    cross = {
        "inventory_tolerance": {"value": 0.0, "status": "OPEN until G1 (DT-079); provisional"},
        "series_cut_agreement": series_cut_agreement(observations, windows, branches),
        "model_level_spearman": model_level_spearman(observations, windows, branches, cut_labels),
        "same_ordering_mase_rmsse_wape_per_series_cut": identical_series_cut_ordering(observations),
    }
    decisions: dict = {}
    engine_versions = set()
    for branch in branches:
        outcomes, reasons = Counter(), Counter()
        for ps in result.products:
            for d in ps.traces[branch].decisions:
                outcomes[d.outcome] += 1
                reasons.update(d.reasons)
                engine_versions.add(d.engine_version)
        decisions[branch] = {"outcomes": dict(sorted(outcomes.items())), "reasons": dict(sorted(reasons.items()))}
    return {
        "windows": windows,
        "cuts": cut_labels,
        "aggregates": aggregates,
        "across_cuts": across_cuts,
        "cross": cross,
        "decisions": decisions,
        "engine_versions": sorted(engine_versions),
        "simulated": [{"product_id": k[0], "location_id": k[1], "segment": segments.get(k, "")} for k in sorted(simulated)],
        "excluded": result.excluded,
        "exogenous_lines": sum(len(ps.exogenous) for ps in result.products),
    }


def _csv(rows: list[list], header: list[str]) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(header)
    writer.writerows(rows)
    return buffer.getvalue()


def _value(v: object) -> str:
    if v is None:
        return ""
    return repr(v) if isinstance(v, float) else str(v)


def detail_csvs(result: SimulationResult, results: dict) -> dict[str, str]:
    fields = ["days", "demand", "consumption", "units_short", "stockout_days", "stockout_rate", "fill_rate",
              "cycle_service_level", "avg_inventory", "avg_inventory_value", "rotation", "units_ordered", "orders"]
    rows = []
    ordered = sorted(results["windows"].items(), key=lambda kv: (kv[0][0], kv[0][1], kv[0][2], MODEL_NAMES.index(kv[0][3])))
    for (cut, pid, loc, branch), w in ordered:
        d = w.as_dict()
        rows.append([cut, pid, loc, branch] + [_value(d[f]) for f in fields])
    windows = _csv(rows, ["as_of", "product_id", "location_id", "model"] + fields)
    orders, decisions = [], []
    for ps in result.products:
        for branch in result.config.branches:
            trace = ps.traces[branch]
            for o in trace.orders:
                orders.append(
                    [branch, ps.key[0], ps.key[1], o.order_id, o.placed_on.isoformat(), str(o.quantity), o.lead_time_days,
                     o.arrival_on.isoformat()]
                )
            for d in trace.decisions:
                decisions.append(
                    [branch, ps.key[0], ps.key[1], d.day.isoformat(), d.outcome, "|".join(d.reasons), d.engine_version,
                     str(d.forecast_available).lower()]
                )
    return {
        WINDOWS_FILE: windows,
        ORDERS_FILE: _csv(
            orders, ["model", "product_id", "location_id", "order_id", "placed_on", "quantity", "lead_time_days", "arrival_on"]
        ),
        DECISIONS_FILE: _csv(
            decisions,
            ["model", "product_id", "location_id", "day", "outcome", "reasons", "engine_version", "forecast_available"],
        ),
    }


def build_summary(config: SimConfig, results: dict, csvs: dict[str, str], metadata: dict) -> dict:
    public = {k: v for k, v in results.items() if k != "windows"}
    digest = hashlib.sha256()
    for name in sorted(csvs):
        digest.update(csvs[name].encode("utf-8"))
    digest.update(json.dumps(public, sort_keys=True, default=str).encode("utf-8"))
    return {
        "label": "SYNTHETIC",
        "unit": "F5b (DT-088)",
        "metadata": metadata,
        "config": config.describe(),
        "results": public,
        "files": {name: hashlib.sha256(text.encode("utf-8")).hexdigest() for name, text in sorted(csvs.items())},
        "results_sha256": digest.hexdigest(),
    }


def compact_json_text(summary: dict) -> str:
    """Versioned summary: metadata, configuration, fingerprint and aggregates; no per-cut detail."""
    results = dict(summary["results"])
    cross = dict(results["cross"])
    cross["model_level_spearman"] = {
        h: {m: {k: v for k, v in s.items() if k != "per_cut"} for m, s in block.items()}
        for h, block in cross["model_level_spearman"].items()
    }
    results["cross"] = cross
    compact = _round(
        {
            "label": summary["label"],
            "unit": summary["unit"],
            "metadata": summary["metadata"],
            "config": summary["config"],
            "results_sha256": summary["results_sha256"],
            "files": summary["files"],
            "results": results,
        }
    )
    text = json.dumps(compact, indent=1, sort_keys=True, ensure_ascii=False, default=str)
    text = _FLAT_LIST.sub(lambda m: "[" + re.sub(r",\n\s*", ", ", m.group(1)) + "]", text)
    return text + "\n"


# --- Markdown -------------------------------------------------------------------------------------------

_PERIOD_LABELS = {PERIOD_FULL: "periodo completo", PERIOD_NO_WARMUP: "sin las semanas de calentamiento"}
_HORIZON_LABELS = {"H1": "h = 1", "LR": "L + R"}


def _f(v: object, digits: int = 3) -> str:
    if v is None:
        return "—"
    if isinstance(v, str):
        try:
            v = float(v)
        except ValueError:
            return v
    return f"{v:,.{digits}f}"


def render_markdown(summary: dict) -> str:
    md, cfg, r = summary["metadata"], summary["config"], summary["results"]
    lines = [
        "# Fase 5 — F5b: simulador de Nivel 2 aplicado a los baselines",
        "",
        "> **SYNTHETIC.** La demanda de la simulación es la demanda latente del dataset sintético (`demand.csv`); con",
        "> datos REAL no existe y este informe no es reproducible tal cual. No elige el baseline oficial, ni la métrica",
        "> primaria (`DT-021`, `DT-078`), ni umbrales o tolerancias (`DT-079`), ni promueve nada (`DT-084`).",
        "> Generado por `python -m ml simulate`; no editar a mano.",
        "",
        "## 1. Ejecución",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Fecha | {md.get('generated_on', '—')} |",
        f"| Comando | `{md.get('command') or '—'}` |",
        f"| Dataset | `{md['dataset_version']}` ({md['data_origin']}) |",
        f"| Código | `ml` {md['ml_version']} |",
        f"| Motor U1 (`ENGINE_VERSION`) | {md['engine_version_u1']}; versiones vistas en las decisiones: {', '.join(r['engine_versions'])} |",
        f"| Commit | `{md['git_commit']}` (cambios sin commit en archivos versionados: {md['git_tracked_changes']}) |",
        f"| Python | {md['python_version']} |",
        f"| Aleatoriedad | {md['seeds']} |",
        f"| `results_sha256` | `{summary['results_sha256']}` |",
        "",
        "## 2. Protocolo (`DT-080`, OD-S1 a OD-S4 aceptadas en `DT-088`)",
        "",
        f"- Periodo: del corte {cfg['first_cut']} (semana 64) al {cfg['period_end']}; nada posterior se lee.",
        "- Bucle cerrado: cada rama ve su propio consumo simulado y su propio inventario; el estado inicial (inventario "
        "reconstruido desde `inventory_movements`, `reserved = 0`, órdenes reales abiertas al primer corte) y los eventos "
        "exógenos son idénticos en todas las ramas. Las órdenes reales emitidas después del primer corte se descartan.",
        "- Día simulado (`DT-038`): recepciones, demanda latente, consumo = mín(disponible, demanda), ventas perdidas = "
        "demanda − consumo; inventario nunca negativo. Decisión cada 7 días tras el consumo del día.",
        "- Cada decisión recalcula el forecast de la rama con su historia simulada y llama a U1 sin cambios (misma "
        "`engine_version` en todas las ramas). Un `RECOMMEND` coloca una orden en la fecha de decisión que llega tras el "
        "`L` usado por el motor; cuenta como tránsito en las decisiones siguientes. **Esto aísla el efecto del forecast "
        "pero no mide la variabilidad del proveedor.**",
        "- Métricas en unidades: unidades faltantes, días y tasa de desabasto, *fill rate*, nivel de servicio por ciclos "
        "de 7 días, inventario medio (disponible al final del día) en unidades y en valor (`unit_cost` del proveedor "
        "preferente), rotación, unidades pedidas y órdenes. Sin costes (`BR-X04`); sin «exceso de inventario» (OD-S4: "
        "sin umbral absoluto) ni «órdenes urgentes» (todas usan el lead time del motor).",
        "",
        "## 3. Valores provisionales y pendientes",
        "",
        f"- Cadencia de reentrenamiento: cada {cfg['retrain_every_weeks']['value']} decisión(es) semanal(es) (provisional).",
        f"- Calentamiento excluido del segundo periodo: {cfg['warmup_weeks']['value']} semanas (provisional).",
        f"- Llegada de las órdenes abiertas al primer corte: `{cfg['open_lines_rule']['value']}` — {cfg['open_lines_rule']['status']}.",
        f"- Tolerancia de inventario del cruce de `DT-078`: {r['cross']['inventory_tolerance']['value']} ({r['cross']['inventory_tolerance']['status']}).",
        "- Modelos de las ramas: los de F5a (SES provisional de `DT-076` punto 7 incluido).",
        "",
        "## 4. Población y decisiones",
        "",
        f"- Series simuladas: {len(r['simulated'])}; órdenes reales abiertas al primer corte (exógenas): {r['exogenous_lines']}.",
        "- Fuera de la simulación (sin `L + R` o no vigentes en el primer corte): "
        + (", ".join(f"producto {e['product_id']} ({e['reason']})" for e in r["excluded"]) or "ninguna")
        + ".",
        "",
        "| Rama | " + " | ".join(sorted({o for d in r["decisions"].values() for o in d["outcomes"]})) + " | Motivos `NOT_CALCULABLE` |",
    ]
    outcomes = sorted({o for d in r["decisions"].values() for o in d["outcomes"]})
    lines.append("|---|" + "---|" * len(outcomes) + "---|")
    for branch in [b for b in MODEL_NAMES if b in r["decisions"]]:
        d = r["decisions"][branch]
        reasons = ", ".join(f"{k}: {v}" for k, v in d["reasons"].items()) or "—"
        lines.append(f"| {MODEL_LABELS[branch]} | " + " | ".join(str(d["outcomes"].get(o, 0)) for o in outcomes) + f" | {reasons} |")
    lines += ["", "## 5. Resultados de Nivel 2 por rama, segmento y periodo (SYNTHETIC)", ""]
    for period, block in r["aggregates"].items():
        lines += [
            f"### {_PERIOD_LABELS[period]} ({block['first']} a {block['last']})",
            "",
            "| Segmento | Rama | Series | Unidades faltantes | Días con desabasto | Tasa de desabasto | *Fill rate* | Servicio por ciclos | Inventario medio | Relativo a media móvil 13 | Valor medio | Rotación | Unidades pedidas | Órdenes |",
            "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
        ]
        for segment, seg in block["segments"].items():
            label = "todos" if segment == ALL_SEGMENTS else SEGMENT_LABELS_ES.get(segment, segment)
            for branch in [b for b in MODEL_NAMES if b in seg["branches"]]:
                a = seg["branches"][branch]
                rel = seg["avg_inventory_relative_to_reference"].get(branch)
                lines.append(
                    f"| {label} | {MODEL_LABELS[branch]} | {a['n_series']} | {_f(a['units_short'], 0)} | {a['stockout_days']} | "
                    f"{_f(a['stockout_rate'])} | {_f(a['fill_rate'])} | {_f(a['cycle_service_level'])} | {_f(a['avg_inventory'], 1)} | "
                    f"{_f(rel)} | {_f(a['avg_inventory_value'], 0)} | {_f(a['rotation'])} | {_f(a['units_ordered'], 0)} | {a['orders']} |"
                )
        lines.append("")
    lines += [
        "### Dispersión entre las ventanas de 14 semanas de los 17 cortes de F5a (todas las series)",
        "",
        "| Rama | Unidades faltantes por ventana: media (de; mín–máx) | *Fill rate* | Tasa de desabasto | Inventario medio |",
        "|---|---|---|---|---|",
    ]
    for branch in [b for b in MODEL_NAMES if b in r["across_cuts"]]:
        s = r["across_cuts"][branch]
        cells = [f"{_f(s[k]['mean'])} ({_f(s[k]['sd'])}; {_f(s[k]['min'])}–{_f(s[k]['max'])})" for k in ("units_short", "fill_rate", "stockout_rate", "avg_inventory")]
        lines.append(f"| {MODEL_LABELS[branch]} | " + " | ".join(cells) + " |")
    cross = r["cross"]
    lines += [
        "",
        "## 6. Cruce informativo con el Nivel 1 (`DT-078`, sin elegir métrica)",
        "",
        "Para cada par de ramas y cada (serie, corte): ¿la métrica candidata de Nivel 1 y las unidades faltantes de Nivel 2 "
        "en las 14 semanas siguientes prefieren la misma rama? Sin contar empates. «Con inventario»: además, la rama "
        "preferida no tiene más inventario medio que la otra (tolerancia `OPEN`, provisional 0).",
        "",
        "| Horizonte de Nivel 1 | Métrica | Pares comparados | Empates | Acuerdo | Acuerdo y restricción de inventario (sobre comparados) | Acuerdos que cumplen la restricción |",
        "|---|---|---|---|---|---|---|",
    ]
    for horizon in HORIZONS:
        for metric, a in cross["series_cut_agreement"].get(horizon, {}).items():
            lines.append(
                f"| {_HORIZON_LABELS[horizon]} | {metric.upper()} | {a['pairs_compared']} | {a['pairs_tied']} | {_f(a['agreement'])} "
                f"| {_f(a['agreement_with_inventory'])} | {_f(a['agreements_meeting_inventory'])} |"
            )
    lines += [
        "",
        f"En cada serie-corte, MASE, RMSSE y WAPE ordenan las ramas igual (las tres son monótonas en |e| con la misma "
        f"escala para todas las ramas): {'sí' if cross['same_ordering_mase_rmsse_wape_per_series_cut'] else 'no'}. Por eso el "
        "acuerdo serie-corte no distingue entre ellas; las diferencias aparecen al agregar.",
        "",
        "Spearman entre las ramas (4 puntos por corte): agregado de la métrica de Nivel 1 frente al total de unidades "
        "faltantes en la ventana, sobre las mismas series.",
        "",
        "| Horizonte | Métrica | ρ medio | mín | máx | Cortes |",
        "|---|---|---|---|---|---|",
    ]
    for horizon in HORIZONS:
        for metric, s in cross["model_level_spearman"].get(horizon, {}).items():
            lines.append(f"| {_HORIZON_LABELS[horizon]} | {metric.upper()} | {_f(s['mean'])} | {_f(s['min'])} | {_f(s['max'])} | {s['n_cuts']} |")
    lines += [
        "",
        "## 7. Salidas",
        "",
        "Junto a este informe se versiona un JSON resumido (mismo nombre, `.json`): metadatos, configuración, huella y "
        "agregados. El detalle (`f5b-windows.csv` por rama × producto × ventana de cada corte, con las mismas claves que "
        "`f5a-observations.csv`; `f5b-orders.csv`; `f5b-decisions.csv`; `f5b-summary.json`) se regenera de forma "
        "determinista con el comando de §1 en `ml/out/`, ignorado por Git. Huellas:",
        "",
    ]
    for name, sha in summary["files"].items():
        lines.append(f"- `{name}`: `{sha}`")
    lines.append("")
    return "\n".join(lines)
