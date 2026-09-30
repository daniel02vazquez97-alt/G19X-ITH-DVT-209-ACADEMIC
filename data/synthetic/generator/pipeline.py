"""W1 - one complete run of the generator, published by promotion (`DT-040`).

Phase 1 - Data.

    check output/  ->  tmp/<id>/  ->  C2 -> C3 -> C6 -> C4 -> C5 -> C7 -> C8
                   ->  verify  ->  promote

**Why.** Rule B2 of `DT-039` can make Component 5 fail *after* Components 2 to 4 have
written. If they wrote into ``output/``, a failed run would leave a partial or mixed
dataset there. W1 removes the possibility structurally: every component writes into a
workspace of its own run, and ``output/`` changes only when the whole run has finished
and the workspace has passed the final verification.

**What this module is not.** It adds no business rule and changes no component: C2, C3,
C6, C4, C5, C7 and C8 are called through their existing ``generate`` functions, with the
workspace as their directory (`DT-040` section 3). C7 records ``scenario_assignment``
(`DT-041`) and C8 validates the materialised workspace and records ``quality_report``
(`DT-042`) before the final verification. The final verification restates
properties the contracts already demand (`DT-025`, `DT-038`, `DT-039`, `V1-13`).

**The guarantee, stated exactly** (`DT-040` section 5). Python offers no primitive that
replaces a non-empty directory in one step, on Linux or on Windows, so the promotion is
two renames on the same file system:

    (a) output/          -> tmp/<id>.anterior      (only if output/ exists)
    (b) tmp/<id>/        -> output/
    (c) if (b) fails:  tmp/<id>.anterior -> output/, and the run fails

What holds:

* a failure in any component or in the verification leaves ``output/`` untouched;
* ``output/`` never holds files of two runs;
* a failure of (b) restores the previous dataset through (c);
* between (a) and (b) ``output/`` does not exist for an instant. If the *process* dies
  exactly there, or if (c) itself fails, the previous dataset is intact in
  ``tmp/<id>.anterior`` and the error names it. That window is not hidden: the promotion
  is **not** an atomic replacement, and this module does not claim it is.

After a successful promotion ``tmp/<id>.anterior`` is deleted; after any failure the
workspace is deleted (decisions of the project lead of 2026-09-29, closing the two
pending details of `DT-040`). Nothing is kept: no backup, no history of datasets.
"""

from __future__ import annotations

import csv
import datetime as _dt
import hashlib
import io
import json
import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from ..config.config import DatasetConfig
from . import (
    catalog,
    demand,
    inventory,
    orders,
    scenarios,
    supplier_behaviour,
    validator,
)
from . import policies as pol
from .catalog import DEFAULT_OUTPUT_DIR
from .rng import (
    COMPONENT_CATALOG,
    COMPONENT_DEMAND,
    COMPONENT_INVENTORY,
    COMPONENT_ORDERS,
    COMPONENT_SCENARIOS,
    COMPONENT_SUPPLIER_BEHAVIOUR,
    COMPONENT_VALIDATOR,
    sub_seed,
)
from .writer import (
    CATALOG_VERSION,
    DEMAND_VERSION,
    GENERATOR_VERSION,
    INVENTORY_VERSION,
    ORDERS_VERSION,
    SCENARIOS_VERSION,
    SUPPLIER_BEHAVIOUR_VERSION,
    VALIDATOR_VERSION,
)

__all__ = [
    "MANIFEST_FILE",
    "TMP_DIR_NAME",
    "PREVIOUS_SUFFIX",
    "FILE_COLUMNS",
    "DATASET_FILES",
    "COMPONENT_VERSIONS",
    "check_output",
    "generate_into",
    "verify",
    "promote",
    "run",
]

MANIFEST_FILE = "manifest.json"

#: `DT-040` section 2: the workspaces live in ``tmp/``, a sibling of ``output/`` - same
#: file system, which is what makes the promotion a rename and not a copy.
TMP_DIR_NAME = "tmp"

#: `DT-040` section 5, step (a): transient name of the dataset being replaced.
PREVIOUS_SUFFIX = ".anterior"

#: The header contract of every data file of a complete run (`DT-024`, `DT-034`,
#: `DT-038`, `DT-039`), taken from the components themselves: nothing is restated here.
FILE_COLUMNS: dict[str, tuple[str, ...]] = {
    "categories.csv": catalog.CATEGORY_COLUMNS,
    "products.csv": catalog.PRODUCT_COLUMNS,
    "suppliers.csv": catalog.SUPPLIER_COLUMNS,
    "product_suppliers.csv": catalog.PRODUCT_SUPPLIER_COLUMNS,
    "locations.csv": catalog.LOCATION_COLUMNS,
    demand.DEMAND_FILE: demand.DEMAND_COLUMNS,
    inventory.CONSUMPTION_FILE: inventory.CONSUMPTION_COLUMNS,
    inventory.MOVEMENTS_FILE: inventory.MOVEMENT_COLUMNS,
    inventory.INVENTORY_FILE: inventory.INVENTORY_COLUMNS,
    orders.PURCHASE_ORDERS_FILE: orders.PURCHASE_ORDER_COLUMNS,
    orders.PURCHASE_ORDER_ITEMS_FILE: orders.PURCHASE_ORDER_ITEM_COLUMNS,
    orders.PURCHASE_ORDER_RECEIPTS_FILE: orders.PURCHASE_ORDER_RECEIPT_COLUMNS,
}

#: Every file a complete run publishes, and nothing else (`DT-038` section 13).
DATASET_FILES = frozenset(FILE_COLUMNS) | {MANIFEST_FILE}

#: Components a complete run records in ``manifest.components``, with their versions:
#: the seven components C2-C8 (W1 is not a component, `DT-042` section 8).
COMPONENT_VERSIONS: dict[str, str] = {
    COMPONENT_CATALOG: CATALOG_VERSION,
    COMPONENT_DEMAND: DEMAND_VERSION,
    COMPONENT_SUPPLIER_BEHAVIOUR: SUPPLIER_BEHAVIOUR_VERSION,
    COMPONENT_INVENTORY: INVENTORY_VERSION,
    COMPONENT_ORDERS: ORDERS_VERSION,
    COMPONENT_SCENARIOS: SCENARIOS_VERSION,
    COMPONENT_VALIDATOR: VALIDATOR_VERSION,
}

#: The two fields contributed by C7 and C8 (`DT-025`, `DT-041`, `DT-042`).
SCENARIO_ASSIGNMENT_FIELD = scenarios.SCENARIO_ASSIGNMENT_FIELD
QUALITY_REPORT_FIELD = validator.QUALITY_REPORT_FIELD


# ---------------------------------------------------------------------------------------
# Step 1 - the output directory before anything is created (DT-038 section 13)
# ---------------------------------------------------------------------------------------


def check_output(output_dir: Path | str) -> None:
    """Rules 1 to 3 of `DT-038` section 13, before the workspace exists.

    Missing or empty: fine. Holding only files of the dataset: fine, they are replaced as
    a block by the promotion. Anything else - a foreign file, a sub-directory, a path
    that is not a directory - fails, naming what was found. Nothing is deleted.
    """
    target = Path(output_dir)
    if not target.exists():
        return
    if not target.is_dir():
        raise pol.GeneratorError([f"{target} exists and is not a directory"])
    foreign = sorted(
        entry.name
        for entry in target.iterdir()
        if entry.name not in DATASET_FILES or not entry.is_file()
    )
    if foreign:
        raise pol.GeneratorError(
            [
                f"{target} holds entries that are not part of the dataset: {foreign}. "
                "Nothing was generated and nothing was deleted (DT-038 section 13)"
            ]
        )


# ---------------------------------------------------------------------------------------
# Step 3 - the five components, in the approved order, inside the workspace
# ---------------------------------------------------------------------------------------


def generate_into(
    config: DatasetConfig,
    workspace: Path,
    *,
    generated_at: _dt.datetime,
) -> dict[str, Any]:
    """Run C2 -> C3 -> C6 -> C4 -> C5 -> C7 -> C8 into ``workspace``; return the manifest.

    Each component is called exactly as its own tests call it; none knows that the
    directory is a workspace (`DT-040` section 3). C7 runs only once every CSV is
    written, with the Component 6 profiles in memory (`DT-041` section 3); C8 runs last
    and reads only the workspace (`DT-042` section 8). A C8 failure raises before
    anything else happens, so the run is never promoted.
    """
    catalog.generate(config, workspace, generated_at=generated_at)
    demand.generate(config, workspace, generated_at=generated_at)
    _, profiles = supplier_behaviour.generate(config, workspace)
    _, simulation = inventory.generate(config, workspace, profiles)
    orders.generate(config, workspace, simulation)
    scenarios.generate(config, workspace, profiles)
    return validator.generate(config, workspace)


# ---------------------------------------------------------------------------------------
# Step 4 - final verification of the workspace (DT-040 section 4)
# ---------------------------------------------------------------------------------------


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _check_inventory_files(workspace: Path) -> list[str]:
    """`V1-13` and `DT-038` section 6 on the written files: no negative stock at any
    point, and a snapshot equal to the signed sum of the movements."""
    problems: list[str] = []
    balance: dict[tuple[str, str], int] = {}
    for row in _read(workspace / inventory.MOVEMENTS_FILE):
        pair = (row["product_id"], row["location_id"])
        balance[pair] = balance.get(pair, 0) + int(row["quantity"])
        if balance[pair] < 0:
            problems.append(f"negative stock for {pair} in {inventory.MOVEMENTS_FILE}")
            break
    for row in _read(workspace / inventory.INVENTORY_FILE):
        pair = (row["product_id"], row["location_id"])
        on_hand = int(row["quantity_on_hand"])
        if on_hand < 0:
            problems.append(f"negative quantity_on_hand for {pair}")
        if on_hand != balance.get(pair, 0):
            problems.append(
                f"{inventory.INVENTORY_FILE} of {pair} is not its movements"
            )
    return problems


def verify(workspace: Path | str) -> dict[str, Any]:
    """Check a finished workspace before anything touches ``output/``.

    Restates what the contracts already require of a published dataset - no new rule:

    * the manifest exists, was produced by this generator version, and lists exactly the
      seven components with their versions and sub-seeds (`DT-025`, `DT-030`);
    * it carries ``scenario_assignment`` and a ``quality_report`` whose result is
      ``PASS`` with ``validations.failed == 0`` and ``executed == passed`` (`DT-042`);
    * the files on disk are exactly ``manifest.files`` plus ``manifest.json``, flat, and
      they are the complete set of a run (`DT-040` section 4, `DT-038` section 13);
    * every ``sha256`` and row count matches the bytes (`DT-025`);
    * every header is its contract (`DT-024`, `DT-034`, `DT-038`, `DT-039`);
    * stock never goes negative and the snapshot is its movements (`V1-13`, `DT-038`).

    Returns:
        The manifest, as read from the workspace.

    Raises:
        GeneratorError: with every problem found.
    """
    root = Path(workspace)
    path = root / MANIFEST_FILE
    if not path.is_file():
        raise pol.GeneratorError([f"{MANIFEST_FILE} is missing from the workspace"])
    manifest = json.loads(path.read_text(encoding="utf-8"))
    problems: list[str] = []

    if manifest.get("generator_version") != GENERATOR_VERSION:
        problems.append(
            f"generator_version is {manifest.get('generator_version')!r}, "
            f"expected {GENERATOR_VERSION!r}"
        )
    if manifest.get("data_origin") != "SYNTHETIC":
        problems.append("manifest data_origin is not SYNTHETIC")
    components = {c["name"]: c for c in manifest.get("components", [])}
    if set(components) != set(COMPONENT_VERSIONS) or len(components) != len(
        manifest.get("components", [])
    ):
        problems.append(
            f"manifest components are {sorted(components)}, "
            f"expected {sorted(COMPONENT_VERSIONS)}"
        )
    for name, version in COMPONENT_VERSIONS.items():
        entry = components.get(name)
        if entry is None:
            continue
        if entry.get("version") != version:
            problems.append(f"component {name} has version {entry.get('version')!r}")
        if entry.get("sub_seed") != sub_seed(manifest.get("seed"), name):
            problems.append(f"component {name} has a wrong sub_seed")

    if not isinstance(manifest.get(SCENARIO_ASSIGNMENT_FIELD), dict):
        problems.append(f"the manifest has no {SCENARIO_ASSIGNMENT_FIELD}")
    report = manifest.get(QUALITY_REPORT_FIELD)
    validations = report.get("validations") if isinstance(report, dict) else None
    if not isinstance(validations, dict):
        problems.append(f"the manifest has no {QUALITY_REPORT_FIELD}")
    elif (
        report.get("result") != "PASS"
        or validations.get("failed") != 0
        or validations.get("executed") != validations.get("passed")
    ):
        problems.append(
            f"{QUALITY_REPORT_FIELD} is not a pass: result {report.get('result')!r}, "
            f"failed {validations.get('failed')!r}, executed "
            f"{validations.get('executed')!r}, passed {validations.get('passed')!r}"
        )

    listed = {f["name"]: f for f in manifest.get("files", [])}
    on_disk = {entry.name for entry in root.iterdir()}
    directories = sorted(entry.name for entry in root.iterdir() if not entry.is_file())
    if directories:
        problems.append(f"the workspace holds directories: {directories}")
    expected_on_disk = set(listed) | {MANIFEST_FILE}
    if on_disk != expected_on_disk:
        problems.append(
            f"files not in the manifest: {sorted(on_disk - expected_on_disk)}; "
            f"listed but missing: {sorted(expected_on_disk - on_disk)}"
        )
    if set(listed) != set(FILE_COLUMNS):
        problems.append(
            f"the manifest does not list a complete dataset: missing "
            f"{sorted(set(FILE_COLUMNS) - set(listed))}, "
            f"unexpected {sorted(set(listed) - set(FILE_COLUMNS))}"
        )

    for name, entry in sorted(listed.items()):
        file_path = root / name
        if not file_path.is_file():
            continue
        data = file_path.read_bytes()
        if hashlib.sha256(data).hexdigest() != entry.get("sha256"):
            problems.append(f"{name}: sha256 does not match the manifest")
        records = list(csv.reader(io.StringIO(data.decode("utf-8"), newline="")))
        if name in FILE_COLUMNS and (
            not records or tuple(records[0]) != FILE_COLUMNS[name]
        ):
            problems.append(f"{name}: header is not its contract")
        if len(records) - 1 != entry.get("rows"):
            problems.append(f"{name}: row count does not match the manifest")

    if not problems:
        problems.extend(_check_inventory_files(root))
    if problems:
        raise pol.GeneratorError(problems)
    return manifest


# ---------------------------------------------------------------------------------------
# Step 5 - promotion (DT-040 section 5)
# ---------------------------------------------------------------------------------------


def promote(workspace: Path, output_dir: Path, previous: Path) -> None:
    """Replace ``output_dir`` with ``workspace`` by the renames of `DT-040` section 5.

    Raises:
        GeneratorError: if the promotion fails. When the previous dataset could not be
            put back, the message says where it is intact.
    """
    had_previous = output_dir.exists()
    if had_previous:
        # (a) If this fails nothing has moved: output/ is untouched.
        try:
            os.rename(output_dir, previous)
        except OSError as exc:
            raise pol.GeneratorError(
                [f"could not move {output_dir} aside ({exc}); it is untouched"]
            ) from exc
    try:
        os.rename(workspace, output_dir)  # (b)
    except OSError as exc:
        if had_previous:
            try:
                os.rename(previous, output_dir)  # (c)
            except OSError as restore_exc:
                raise pol.GeneratorError(
                    [
                        f"promotion failed ({exc}) and the previous dataset could not "
                        f"be put back ({restore_exc}); it is intact in {previous} - "
                        f"rename it to {output_dir}"
                    ]
                ) from restore_exc
        raise pol.GeneratorError(
            [f"promotion failed ({exc}); the previous dataset is in place, unchanged"]
        ) from exc
    if had_previous:
        try:
            shutil.rmtree(previous)
        except OSError as exc:
            raise pol.GeneratorError(
                [
                    f"the new dataset is published in {output_dir}, but the replaced "
                    f"one could not be deleted from {previous} ({exc})"
                ]
            ) from exc


# ---------------------------------------------------------------------------------------
# The whole run
# ---------------------------------------------------------------------------------------


def run(
    config: DatasetConfig,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
    *,
    generated_at: _dt.datetime | None = None,
) -> dict[str, Any]:
    """Generate a complete dataset and publish it into ``output_dir`` (`DT-040` §4).

    The workspace is ``<output_dir's parent>/tmp/<execution id>/``; the id is a random
    UUID used **only** as a directory name, never written into the dataset.

    Returns:
        The published manifest.

    Raises:
        GeneratorError: if ``output_dir`` holds foreign entries, if any component or the
            final verification fails, or if the promotion fails. In every case the
            workspace is deleted and ``output_dir`` holds exactly what it held before -
            except for the double failure described in :func:`promote`, whose message
            names where the previous dataset is.
    """
    output = Path(output_dir)
    check_output(output)

    tmp_root = output.parent / TMP_DIR_NAME
    execution_id = uuid.uuid4().hex
    workspace = tmp_root / execution_id
    previous = tmp_root / (execution_id + PREVIOUS_SUFFIX)
    tmp_root.mkdir(parents=True, exist_ok=True)
    workspace.mkdir()
    moment = generated_at or _dt.datetime.now(_dt.timezone.utc)
    try:
        generate_into(config, workspace, generated_at=moment)
        manifest = verify(workspace)
        promote(workspace, output, previous)
    finally:
        # The workspace never survives the run: promoted (renamed away) or deleted.
        # A `previous` left behind by a double failure is NOT touched: it may be the
        # only copy of the previous dataset.
        if workspace.exists():
            shutil.rmtree(workspace)
        try:
            tmp_root.rmdir()  # only if empty
        except OSError:
            pass
    return manifest
