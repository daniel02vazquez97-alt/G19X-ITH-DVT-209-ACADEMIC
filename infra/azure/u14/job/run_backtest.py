"""U14 (DT-102): reproduce in Azure Machine Learning the F5a backtest of the official baseline and log it with MLflow.

Runs inside the command job of infra/azure/u14/job/job.yml, from the code snapshot that deploy-u14.ps1 assembles
(backend/app, ml/, data/synthetic without output, the versioned F5a summary and this folder):

1. publishes the synthetic dataset 0.4.0 with the generator, unchanged (``python -m data.synthetic.generator``);
2. runs ``python -m ml backtest`` unchanged (``ml/`` keeps only the standard library, DT-094 point 9);
3. compares its ``results_sha256`` with docs/reports/fase5-f5a-backtest-sintetico.json (the acceptance criterion);
4. logs parameters, the aggregated metrics of every baseline, the comparison and the reports with MLflow, when the
   job provides a tracking URI (Azure ML does); locally it only prints them;
5. writes the folder of the ``baseline-ma13`` model: the configuration of the official baseline (DT-056, DT-089), the
   comparison and the report.

MLflow lives here, outside ``ml/``. The script never changes a result: a different hash is recorded as such and the
exit code says it (2), so Verify fails instead of registering a model that does not reproduce the report.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
VERSIONED = ROOT / "docs" / "reports" / "fase5-f5a-backtest-sintetico.json"
GENERATED_ON = "2026-10-05"  # the date of the versioned report: metadata only, not part of results_sha256
OFFICIAL = "baseline.moving_average"
HORIZON, PERIOD, SEGMENT = "H1", "ALL_WEEKS", "ALL"
METRICS = ("mase", "wape", "mae", "rmse", "bias", "coverage")
MODEL_CONFIG = {
    "name": "baseline-ma13",
    "baseline": OFFICIAL,
    "baseline_version": "1.0.0",
    "window_weeks": 13,
    "interval": {"method": "empirical_quantiles", "lower": 0.10, "upper": 0.90, "nominal_level": 0.80},
    "decisions": ["DT-056", "DT-089", "DT-090", "DT-091"],
    "data_origin": "SYNTHETIC",
    "note": "Configuracion del baseline oficial; el pronostico de la aplicacion lo calcula backend/app/forecasting (U3).",
}


def aggregated_metrics(summary: dict) -> dict[str, float]:
    """Mean over the 17 cuts of each metric of each baseline (H1, all weeks, whole catalogue): ``<baseline>.<metric>``."""
    block = summary["aggregates"][HORIZON][PERIOD][SEGMENT]
    result: dict[str, float] = {}
    for baseline in sorted(block):
        metrics = block[baseline]["metrics"]
        for name in METRICS:
            if name in metrics and metrics[name]:
                result[f"{baseline}.{name}"] = float(metrics[name][0])
    return result


def comparison(produced: dict, versioned: dict) -> dict:
    return {
        "results_sha256": produced["results_sha256"],
        "versioned_results_sha256": versioned["results_sha256"],
        "reproduces_versioned_report": produced["results_sha256"] == versioned["results_sha256"],
        "dataset_version": produced["metadata"].get("dataset_version"),
        "python_version": produced["metadata"].get("python_version"),
    }


def write_model(model_dir: Path, report_json: Path, report_md: Path, result: dict) -> None:
    model_dir.mkdir(parents=True, exist_ok=True)
    (model_dir / "baseline-ma13.json").write_text(json.dumps(MODEL_CONFIG, indent=2, ensure_ascii=False) + "\n",
                                                  encoding="utf-8")
    (model_dir / "comparison.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    shutil.copy2(report_json, model_dir / "f5a-report.json")
    shutil.copy2(report_md, model_dir / "f5a-report.md")


def run(command: list[str], env: dict[str, str] | None = None) -> None:
    print("+", " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, env=env, check=True)


def log_mlflow(result: dict, metrics: dict[str, float], report_dir: Path) -> bool:
    """Logs to the run Azure ML opens for the job; False when there is no tracking URI (local run)."""
    if not os.environ.get("MLFLOW_TRACKING_URI"):
        return False
    import mlflow  # installed by job/requirements.txt; never imported by ml/

    with mlflow.start_run():
        mlflow.log_params({"dataset_version": result["dataset_version"], "python_version": result["python_version"],
                           "population": "as_of_validity", "official_baseline": OFFICIAL, "horizon": HORIZON})
        mlflow.log_metrics({k.replace("baseline.", ""): v for k, v in metrics.items()})
        mlflow.log_metric("reproduces_versioned_report", 1.0 if result["reproduces_versioned_report"] else 0.0)
        mlflow.set_tags({"results_sha256": result["results_sha256"],
                         "versioned_results_sha256": result["versioned_results_sha256"], "unit": "U14", "decision": "DT-102"})
        mlflow.log_artifacts(str(report_dir), artifact_path="f5a")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--model-dir", type=Path, required=True, help="output folder of the baseline-ma13 model")
    args = parser.parse_args(argv)
    run([sys.executable, "-m", "data.synthetic.generator"])
    work = Path(tempfile.mkdtemp(prefix="u14-"))
    report_md = work / "report" / "fase5-f5a-backtest-sintetico.md"
    report_md.parent.mkdir(parents=True)
    env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
    run([sys.executable, "-m", "ml", "backtest", "--data", "data/synthetic/output", "--out", str(work / "out"),
         "--report", str(report_md), "--generated-on", GENERATED_ON], env=env)
    report_json = report_md.with_suffix(".json")
    produced = json.loads(report_json.read_text(encoding="utf-8"))
    versioned = json.loads(VERSIONED.read_text(encoding="utf-8"))
    result = comparison(produced, versioned)
    metrics = aggregated_metrics(produced)
    print(json.dumps(result, indent=2))
    print(json.dumps(metrics, indent=2))
    write_model(args.model_dir, report_json, report_md, result)
    logged = log_mlflow(result, metrics, report_md.parent)
    print("MLflow:", "registrado en el job" if logged else "sin URI de seguimiento (ejecucion local)")
    return 0 if result["reproduces_versioned_report"] else 2


if __name__ == "__main__":
    sys.exit(main())
