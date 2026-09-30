"""Command-line entry point for the synthetic dataset generator.

    python3 -m data.synthetic.generator [--config PATH] [--output DIR]

Run from the repository root. Runs one complete execution of the generator through W1
(`DT-040`, :mod:`.pipeline`): C2 -> C3 -> C6 -> C4 -> C5 -> C7 -> C8 inside a workspace of its own
(``<output>/../tmp/<id>/``), a final verification, and only then the promotion of the
workspace to the output directory (``data/synthetic/output/`` by default). If anything
fails, the output directory keeps exactly what it held before.

Then prints a short summary of what was published.

Exit codes: ``0`` on success, ``1`` if the configuration or the generator rejects the
request. Both failures print every problem found, not just the first one.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..config.config import ConfigError, load_config
from . import pipeline
from .catalog import DEFAULT_OUTPUT_DIR
from .policies import GeneratorError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python3 -m data.synthetic.generator",
        description=(
            "Generate and publish the synthetic dataset "
            "(C2 -> C3 -> C6 -> C4 -> C5 -> C7 -> C8)."
        ),
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=None,
        help="configuration file (default: data/synthetic/config/dataset_config.yaml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    args = parser.parse_args(argv)

    try:
        config = load_config(args.config)
    except (ConfigError, FileNotFoundError) as exc:
        print(exc, file=sys.stderr)
        return 1

    try:
        # W1: nothing is written to the output directory until the run is complete
        # and verified (DT-040).
        manifest = pipeline.run(config, args.output)
    except GeneratorError as exc:
        print(exc, file=sys.stderr)
        return 1

    print(
        f"dataset {manifest['dataset_version']} "
        f"(generator {manifest['generator_version']}) published -> {args.output}"
    )
    for entry in manifest["files"]:
        print(f"  {entry['name']:<24} {entry['rows']:>6} rows  {entry['entity']}")
    print("  manifest.json")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
