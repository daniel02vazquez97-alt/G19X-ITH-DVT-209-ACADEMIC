"""Deterministic outputs of an F5a run: detail CSVs, JSON summary and the Markdown report.

* ``f5a-observations.csv`` — one row per model × cut × series × horizon (input of the series-cut
  agreement of `DT-078`; no Level 2 is computed here);
* ``f5a-series-cuts.csv`` — training-side description of every series-cut (segment, scale, ``L``);
* ``f5a-summary.json`` — run metadata, provisional configuration, per-cut summaries and the
  comparison tables;
* the Markdown report, labelled SYNTHETIC, without promotion conclusions or metric choice.

``results_sha256`` covers the two CSVs and the tables (not the run metadata), so two runs on the
same data and code give the same hash.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import io
import json
import platform
import subprocess
from pathlib import Path

from app.forecasting import BASELINES
from app.supply_engine import ENGINE_VERSION

from . import ML_VERSION
from .backtest import ALL_SEGMENTS, H1, HORIZONS, LR, VIEW_ALL, VIEW_NO_STOCKOUT, VIEWS, BacktestResult, common_keys
from .config import F5aConfig
from .cuts import HOLDOUT_CUT, LAST_READABLE_DATE
from .metrics import Observation
from .models import MODEL_NAMES, SES_NAME, SES_VERSION
from .segmentation import SEGMENT_LABELS_ES, SEGMENTS

OBSERVATIONS_FILE = "f5a-observations.csv"
SERIES_CUTS_FILE = "f5a-series-cuts.csv"
SUMMARY_FILE = "f5a-summary.json"

MODEL_LABELS = {
    "baseline.naive": "naïve",
    "baseline.seasonal_naive": "naïve estacional",
    "baseline.moving_average": "media móvil 13",
    SES_NAME: "SES (provisional)",
}


def _num(value: float | None) -> str:
    return "" if value is None else repr(value)


def observations_csv(result: BacktestResult) -> str:
    common = common_keys(result.observations)
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        ["as_of", "product_id", "location_id", "model", "horizon", "days", "segment", "stockout", "in_common_set",
         "forecast", "actual", "lower", "upper", "error", "scaled_abs_error", "scaled_rms_error", "scale_abs", "scale_sq"]
    )
    for o in sorted(result.observations, key=_obs_order):
        writer.writerow(
            [o.as_of, o.product_id, o.location_id, o.model, o.horizon, o.days, o.segment, str(o.stockout).lower(),
             str((o.as_of, o.product_id, o.location_id, o.horizon) in common).lower(),
             _num(o.forecast), _num(o.actual), _num(o.lower), _num(o.upper), _num(o.error),
             _num(o.scaled_abs), _num(o.scaled_rms), _num(o.scale_abs), _num(o.scale_sq)]
        )
    return buffer.getvalue()


def _obs_order(o: Observation) -> tuple:
    return (o.as_of, o.product_id, o.location_id, MODEL_NAMES.index(o.model), HORIZONS.index(o.horizon))


def series_cuts_csv(result: BacktestResult) -> str:
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerow(
        ["as_of", "product_id", "location_id", "in_population", "exclusion_reason", "segment", "weeks", "nonzero_weeks",
         "zero_share", "adi", "cv2", "scale_abs", "scale_sq", "supplier_id", "lead_time_days", "lead_time_source",
         "lead_time_observations", "lead_time_capped", "coverage_days", "ses_alpha", "ses_failure"]
        + [f"eligible_{m}" for m in MODEL_NAMES]
    )
    for sc in sorted(result.series_cuts, key=lambda s: (s.as_of, s.key)):
        f, p = sc.feats, sc.protection
        ses = sc.forecasts.get(SES_NAME)
        writer.writerow(
            [sc.as_of.isoformat(), sc.key[0], sc.key[1], str(sc.in_population).lower(), sc.exclusion_reason or "",
             sc.segment or "", f.weeks if f else "", f.nonzero_weeks if f else "", _num(f.zero_share) if f else "",
             _num(f.adi) if f else "", _num(f.cv2) if f else "",
             _num(sc.scale_abs) if f else "", _num(sc.scale_sq) if f else "",
             p.supplier_id if p else "", p.lead_time_days if p else "", p.lead_time_source.value if p else "",
             p.observation_count if p else "", str(p.capped).lower() if p else "", p.coverage_days if p else "",
             f"{ses.alpha:.2f}" if ses and ses.alpha is not None else "", sc.ses_failure or ""]
            + [str(m in sc.forecasts).lower() for m in MODEL_NAMES]
        )
    return buffer.getvalue()


def _git(*args: str) -> str | None:
    try:
        done = subprocess.run(
            ["git", *args], cwd=Path(__file__).resolve().parents[1], capture_output=True, text=True, timeout=30, check=True
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return done.stdout.strip()


def run_metadata(dataset_version: str, data_origin: str, generated_on: _dt.date, command: str = "") -> dict:
    """Traceability of the run (`DT-073`): date, dataset, code versions, commit and Python (outside the hash)."""
    commit = _git("rev-parse", "HEAD")
    status = _git("status", "--porcelain", "--untracked-files=no")
    return {
        "generated_on": generated_on.isoformat(),
        "command": command,
        "dataset_version": dataset_version,
        "data_origin": data_origin,
        "ml_version": ML_VERSION,
        "engine_version_u1": ENGINE_VERSION,
        "baselines_u3": {d.name: d.version for d in BASELINES},
        "ses": {"name": SES_NAME, "version": SES_VERSION},
        "git_commit": commit or "unknown",
        "git_tracked_changes": None if status is None else bool(status),
        "python_version": platform.python_version(),
        "seeds": "none (no randomness)",
    }


_COMPARED_METRICS = ("mase", "rmsse", "wape", "mae", "bias_rel")


def rule_comparison(runs: dict[str, tuple[dict, list[dict]]]) -> dict:
    """Compact comparison of population rules: ``{rule: (tables, per_cut)}`` → n and mean metrics.

    ``n_by_segment``: observations of the common set per horizon, view and segment (equal for every
    model); ``metrics``: mean across cuts per model, all segments together.
    """
    out: dict = {"rules": list(runs), "population_by_cut": {}, "n_by_segment": {}, "metrics": {}}
    for rule, (tables, per_cut) in runs.items():
        for c in per_cut:
            out["population_by_cut"].setdefault(c["as_of"], {})[rule] = c["population"]
        for horizon, views in tables.items():
            for view, segments in views.items():
                for segment, models in segments.items():
                    first = next(iter(models.values()))
                    out["n_by_segment"].setdefault(rule, {}).setdefault(horizon, {}).setdefault(view, {})[segment] = first[
                        "n_observations"
                    ]
                    if segment == ALL_SEGMENTS:
                        for model, entry in models.items():
                            out["metrics"].setdefault(rule, {}).setdefault(horizon, {}).setdefault(view, {})[model] = {
                                m: entry["across_cuts"][m]["mean"] for m in _COMPARED_METRICS
                            }
    return out


def build_summary(
    result: BacktestResult,
    config: F5aConfig,
    tables: dict,
    per_cut: list[dict],
    metadata: dict,
    comparison: dict | None = None,
    discontinued: list[dict] | None = None,
) -> tuple[dict, str, str]:
    obs_csv = observations_csv(result)
    sc_csv = series_cuts_csv(result)
    digest = hashlib.sha256()
    results = {"tables": tables, "cuts": per_cut, "comparison": comparison, "discontinued": discontinued}
    for part in (obs_csv, sc_csv, json.dumps(results, sort_keys=True)):
        digest.update(part.encode("utf-8"))
    summary = {
        "label": "SYNTHETIC",
        "unit": "F5a (DT-086)",
        "metadata": metadata,
        "protocol": {
            "cuts": [c.isoformat() for c in result.cuts],
            "horizon_weeks": 14,
            "holdout_cut": HOLDOUT_CUT.isoformat(),
            "last_readable_date": LAST_READABLE_DATE.isoformat(),
            "window": "expanding",
            "horizons": {H1: "week 1 (7 days)", LR: "L + R days per product (U1 rules, demand_over_horizon)"},
            "views": {VIEW_ALL: "all targets", VIEW_NO_STOCKOUT: "targets without any stockout day"},
            "comparison_set": "series-cut-horizon where every model is eligible and the truth is fully observed",
        },
        "config": config.describe(),
        "cuts": per_cut,
        "tables": tables,
        "population_comparison": comparison,
        "discontinued": discontinued,
        "files": {
            OBSERVATIONS_FILE: hashlib.sha256(obs_csv.encode("utf-8")).hexdigest(),
            SERIES_CUTS_FILE: hashlib.sha256(sc_csv.encode("utf-8")).hexdigest(),
        },
        "results_sha256": digest.hexdigest(),
    }
    return summary, obs_csv, sc_csv


def write_outputs(out_dir: Path, summary: dict, obs_csv: str, sc_csv: str) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / OBSERVATIONS_FILE).write_text(obs_csv, encoding="utf-8", newline="\n")
    (out_dir / SERIES_CUTS_FILE).write_text(sc_csv, encoding="utf-8", newline="\n")
    text = json.dumps(summary, indent=1, sort_keys=True, ensure_ascii=False) + "\n"
    (out_dir / SUMMARY_FILE).write_text(text, encoding="utf-8", newline="\n")


# --- Markdown -----------------------------------------------------------------------------------------


def _fmt(value: float | None, digits: int = 3) -> str:
    return "—" if value is None else f"{value:.{digits}f}"


def _cell(stats: dict) -> str:
    if stats["mean"] is None:
        return "—"
    return f"{_fmt(stats['mean'])} ({_fmt(stats['sd'])}; {_fmt(stats['min'])}–{_fmt(stats['max'])})"


_GROUPS = (
    ("escaladas y relativas", ("mase", "rmsse", "wape", "bias_rel")),
    ("absolutas, sesgo, cobertura y MAPE informativa", ("mae", "rmse", "bias", "coverage", "mape")),
)
_METRIC_LABELS = {
    "mase": "MASE", "rmsse": "RMSSE", "wape": "WAPE", "bias_rel": "sesgo relativo", "mae": "MAE", "rmse": "RMSE",
    "bias": "sesgo", "coverage": "cobertura", "mape": "MAPE (inf.)",
}
_HORIZON_LABELS = {H1: "h = 1 (semana 1)", LR: "L + R (horizonte de protección)"}
_VIEW_LABELS = {VIEW_ALL: "todas las semanas", VIEW_NO_STOCKOUT: "solo objetivos sin desabasto"}


def render_markdown(summary: dict) -> str:
    md = summary["metadata"]
    cfg = summary["config"]
    lines = [
        "# Fase 5 — F5a: backtesting de baselines, Nivel 1 y segmentación provisional",
        "",
        "> **SYNTHETIC.** Evidencia sobre el dataset sintético; debe revalidarse con datos REAL (`docs/05` §20).",
        "> Este informe **no** elige el baseline oficial, ni la métrica primaria (`DT-021`, `DT-078`), ni umbrales",
        "> (`DT-077`, `DT-079`), ni promueve nada (`DT-084`). Las cifras se presentan sin conclusiones de promoción.",
        "> Generado por `python -m ml backtest`; no editar a mano.",
        "",
        "## 1. Ejecución",
        "",
        "| Campo | Valor |",
        "|---|---|",
        f"| Fecha | {md.get('generated_on', '—')} |",
        f"| Comando | `{md.get('command') or '—'}` |",
        f"| Dataset | `{md['dataset_version']}` ({md['data_origin']}) |",
        f"| Código F5a | `ml` {md['ml_version']} |",
        f"| Motor U1 (`ENGINE_VERSION`) | {md['engine_version_u1']} |",
        f"| Baselines U3 | {', '.join(f'`{k}` {v}' for k, v in md['baselines_u3'].items())} |",
        f"| SES | `{md['ses']['name']}` {md['ses']['version']} (PROPUESTA, `DT-076` punto 7) |",
        f"| Commit | `{md['git_commit']}` (cambios sin commit en archivos versionados: {md['git_tracked_changes']}) |",
        f"| Python | {md['python_version']} |",
        f"| Aleatoriedad | {md['seeds']} |",
        f"| `results_sha256` | `{summary['results_sha256']}` |",
        "",
        "## 2. Protocolo (`DT-075`, `DT-076`)",
        "",
        f"- 17 cortes, ventana expansiva, horizonte de 14 semanas: {', '.join(summary['protocol']['cuts'])}.",
        f"- *Holdout*: corte {summary['protocol']['holdout_cut']}; ningún camino lee datos posteriores al "
        f"{summary['protocol']['last_readable_date']} (guarda en el lector y en cada corte).",
        "- Horizontes: `h = 1` y `L + R` días por producto (`L` con las reglas de U1 en el corte, `R = 7`; demanda con "
        "`supply_engine.rules.demand_over_horizon`, exacta como en el motor).",
        "- Verdad: consumo observado; nunca `demand.csv` ni valores imputados. Dos vistas: todas las semanas y solo "
        "objetivos sin ningún día con desabasto.",
        "- Comparación: solo sobre el conjunto común serie-corte-horizonte (todos los modelos elegibles y verdad "
        "completa). Celdas: media entre cortes (desviación poblacional; mínimo–máximo).",
        "- Error `e = F − Y`: sesgo positivo = sobrepronóstico. MASE/RMSSE escaladas con el naïve a un paso dentro del "
        "entrenamiento de cada corte.",
        "",
        "## 3. Valores provisionales usados (PROPUESTA)",
        "",
        f"- Población por corte: `{cfg['population_rule']}` ({cfg.get('population_rule_source', '—')}); la otra regla se "
        "compara en §6.",
        f"- SES: rejilla α {cfg['ses']['alpha_grid'][0]}–{cfg['ses']['alpha_grid'][-1]} (paso 0,05); {cfg['ses']['selection']}; "
        f"nivel inicial `{cfg['ses']['initial_level']}`; mínimo {cfg['ses']['min_history_weeks']} semanas; {cfg['ses']['interval']}.",
        f"- Segmentación: ADI ≥ {cfg['segmentation']['adi_threshold']}, CV² ≥ {cfg['segmentation']['cv2_threshold']}, "
        f"histórico corto < {cfg['segmentation']['short_history_weeks']} semanas; estacionalidad {cfg['segmentation']['seasonality']}.",
        f"- Denominador cero de MASE/RMSSE: `{cfg['level1']['zero_scale_policy']}`; escala en L + R: `{cfg['level1']['lr_scale_policy']}`.",
        f"- Política de U1 para `L`: {cfg['u1_policy']}.",
        "",
        "## 4. Población, elegibilidad y segmentos por corte",
        "",
        "| Corte | Población | Excluidos | " + " | ".join(MODEL_LABELS[m] for m in MODEL_NAMES)
        + " | Común h=1 | Común L+R | Desabasto h=1 | Desabasto L+R | L+R días (mín–máx) | Segmentos |",
        "|---|---|---|" + "---|" * len(MODEL_NAMES) + "---|---|---|---|---|---|",
    ]
    for c in summary["cuts"]:
        excluded = ", ".join(f"{k}: {v}" for k, v in c["excluded"].items()) or "0"
        segments = ", ".join(f"{SEGMENT_LABELS_ES.get(k, k)} {v}" for k, v in c["segments"].items())
        lr = f"{c['lr_days']['min']}–{c['lr_days']['max']}" if c["lr_days"] else "—"
        lines.append(
            f"| {c['as_of']} | {c['population']} | {excluded} | "
            + " | ".join(str(c["eligible_by_model"][m]) for m in MODEL_NAMES)
            + f" | {c['common_set'][H1]} | {c['common_set'][LR]}"
            + f" | {c['stockout_targets'][H1]} | {c['stockout_targets'][LR]} | {lr} | {segments} |"
        )
    lines += _population_notes(summary)
    lines += ["", "## 5. Resultados de Nivel 1 (SYNTHETIC)", ""]
    section = 1
    for horizon in HORIZONS:
        for view in VIEWS:
            block = summary["tables"].get(horizon, {}).get(view, {})
            for title, metrics in _GROUPS:
                if horizon == LR and "coverage" in metrics:
                    metrics = tuple(m for m in metrics if m != "coverage")
                lines += [
                    f"### 5.{section} {_HORIZON_LABELS[horizon]} — {_VIEW_LABELS[view]} — {title}",
                    "",
                    "| Segmento | Modelo | n | " + " | ".join(_METRIC_LABELS[m] for m in metrics) + " |",
                    "|---|---|---|" + "---|" * len(metrics),
                ]
                for segment in (ALL_SEGMENTS,) + SEGMENTS:
                    for model in MODEL_NAMES:
                        entry = block.get(segment, {}).get(model)
                        if entry is None:
                            continue
                        label = "todos" if segment == ALL_SEGMENTS else SEGMENT_LABELS_ES[segment]
                        lines.append(
                            f"| {label} | {MODEL_LABELS[model]} | {entry['n_observations']} | "
                            + " | ".join(_cell(entry["across_cuts"][m]) for m in metrics) + " |"
                        )
                lines.append("")
                section += 1
    lines += [
        "La cobertura no se informa en `L + R`: los intervalos son semanales y no existe una regla documentada para "
        "agregarlos al horizonte de protección.",
        "",
    ]
    lines += _comparison_section(summary)
    lines += [
        "## 7. Salidas para `DT-078` (sin Nivel 2) y datos detallados",
        "",
        f"`{OBSERVATIONS_FILE}` contiene, por modelo × corte × serie × horizonte, el error y su versión escalada "
        "(MASE/RMSSE de la serie-corte) y la marca de conjunto común; con ello se calculan después el acuerdo "
        "serie-corte y el Spearman entre modelos cuando F5b aporte el indicador de Nivel 2. Los datos detallados "
        f"(`{OBSERVATIONS_FILE}`, `{SERIES_CUTS_FILE}` y `{SUMMARY_FILE}`, con las métricas por corte) no se versionan: "
        "se regeneran de forma determinista con el comando de §1 en el directorio de salida (`ml/out/`, ignorado por "
        "Git). Huellas de los CSV:",
        "",
    ]
    for name, sha in summary["files"].items():
        lines.append(f"- `{name}`: `{sha}`")
    lines.append("")
    return "\n".join(lines)


_RULE_LABELS = {"AS_OF_VALIDITY": "vigencia al corte (DT-087)", "U3_SNAPSHOT": "literal de U3"}


def _runs(values: list[tuple[str, object]]) -> str:
    """``[(cut, value)]`` → ``value (first–last)`` for each run of equal consecutive values."""
    parts, start = [], 0
    for i in range(1, len(values) + 1):
        if i == len(values) or values[i][1] != values[start][1]:
            first, last = values[start][0], values[i - 1][0]
            span = first if first == last else f"{first} a {last}"
            parts.append(f"{values[start][1]} ({span})")
            start = i
    return "; ".join(parts)


def _population_notes(summary: dict) -> list[str]:
    cuts = summary["cuts"]
    rule = summary["config"]["population_rule"]
    lines = [
        "",
        "### 4.1 Población, descontinuados y series fuera de L + R",
        "",
        f"- Población por corte con la regla {_RULE_LABELS.get(rule, rule)}: "
        + _runs([(c["as_of"], c["population"]) for c in cuts])
        + f", de {cuts[0]['candidates']} candidatas.",
        "- Fuera de la población (`INACTIVE_OR_OUT_OF_VALIDITY`; en el desglose por segmento figuran como "
        "«descontinuado»): "
        + _runs([(c["as_of"], ", ".join(map(str, c["excluded_ids"].get("INACTIVE_OR_OUT_OF_VALIDITY", []))) or "ninguno") for c in cuts])
        + ". «Población» y «descontinuado» suman siempre las candidatas.",
        "- Productos con `is_active = false` en la foto del dataset que están dentro de la población: "
        + _runs([(c["as_of"], c["snapshot_inactive_in_population"]["n"]) for c in cuts])
        + ".",
        "- Sin proveedor preferente activo (U1 se detiene antes de `H`: fuera de `L + R`, dentro de `h = 1`): productos "
        + _runs([(c["as_of"], ", ".join(map(str, c["no_preferred_supplier"])) or "ninguno") for c in cuts])
        + ". El `is_active` de los proveedores es una foto sin historial: no se infiere ni se reconstruye (`DT-087`).",
    ]
    disc = summary.get("discontinued") or []
    if disc:
        lines += [
            "",
            "Productos con `valid_to` dentro del periodo legible: segmento mientras estaban en la población y recuento "
            "sobre el calendario de 156 semanas contando como cero las semanas posteriores a `valid_to` (cómo los "
            "clasificaría una medición del periodo completo como la orientativa de `DT-077`: 80 suaves, 19 "
            "intermitentes y 1 irregular). El recuento solo usa `valid_to`, un dato maestro; no lee datos posteriores.",
            "",
            "| Producto | `is_active` (foto) | `valid_to` | Último corte en población | Segmento mientras vigente "
            "| Semanas no nulas / 156 | ADI (calendario completo) | CV² | Segmento (calendario completo) |",
            "|---|---|---|---|---|---|---|---|---|",
        ]
        for d in disc:
            segs = ", ".join(f"{SEGMENT_LABELS_ES.get(k, k)} ×{v}" for k, v in d["segments_while_valid"].items()) or "—"
            lines.append(
                f"| {d['product_id']} | {str(d['snapshot_active']).lower()} | {d['valid_to']} | {d['last_cut_in_population'] or '—'} "
                f"| {segs} | {d['padded_nonzero_weeks']} / {d['padded_weeks']} | {_fmt(d['padded_adi'])} | {_fmt(d['padded_cv2'])} "
                f"| {SEGMENT_LABELS_ES.get(d['padded_segment'], d['padded_segment'])} |"
            )
    return lines


def _comparison_section(summary: dict) -> list[str]:
    comp = summary.get("population_comparison")
    if not comp:
        return []
    a, b = comp["rules"]
    la, lb = _RULE_LABELS.get(a, a), _RULE_LABELS.get(b, b)
    lines = [
        "## 6. Comparación de reglas de población (efecto del sesgo de supervivencia)",
        "",
        f"Misma ejecución con las dos reglas: **{la}** (la de este informe) y **{lb}**. Diferencias descriptivas, "
        "`SYNTHETIC`; sin conclusiones de promoción ni elección de métrica.",
        "",
        f"Población por corte — {la}: "
        + _runs([(cut, v[a]) for cut, v in sorted(comp["population_by_cut"].items())])
        + f"; {lb}: "
        + _runs([(cut, v[b]) for cut, v in sorted(comp["population_by_cut"].items())])
        + ".",
        "",
        f"| Horizonte | Vista | Segmento | n ({la}) | n ({lb}) |",
        "|---|---|---|---|---|",
    ]
    for horizon in HORIZONS:
        for view in VIEWS:
            na = comp["n_by_segment"].get(a, {}).get(horizon, {}).get(view, {})
            nb = comp["n_by_segment"].get(b, {}).get(horizon, {}).get(view, {})
            for segment in (ALL_SEGMENTS,) + SEGMENTS:
                if segment in na or segment in nb:
                    label = "todos" if segment == ALL_SEGMENTS else SEGMENT_LABELS_ES[segment]
                    lines.append(
                        f"| {_HORIZON_LABELS[horizon]} | {_VIEW_LABELS[view]} | {label} | {na.get(segment, 0)} | {nb.get(segment, 0)} |"
                    )
    lines += [
        "",
        f"Media entre cortes, todos los segmentos (celda: {la} / {lb}):",
        "",
        "| Horizonte | Vista | Modelo | " + " | ".join(_METRIC_LABELS[m] for m in _COMPARED_METRICS) + " |",
        "|---|---|---|" + "---|" * len(_COMPARED_METRICS),
    ]
    for horizon in HORIZONS:
        for view in VIEWS:
            for model in MODEL_NAMES:
                ma = comp["metrics"].get(a, {}).get(horizon, {}).get(view, {}).get(model)
                mb = comp["metrics"].get(b, {}).get(horizon, {}).get(view, {}).get(model)
                if ma is None and mb is None:
                    continue
                cells = [
                    f"{_fmt((ma or {}).get(m))} / {_fmt((mb or {}).get(m))}" for m in _COMPARED_METRICS
                ]
                lines.append(f"| {_HORIZON_LABELS[horizon]} | {_VIEW_LABELS[view]} | {MODEL_LABELS[model]} | " + " | ".join(cells) + " |")
    lines.append("")
    return lines
