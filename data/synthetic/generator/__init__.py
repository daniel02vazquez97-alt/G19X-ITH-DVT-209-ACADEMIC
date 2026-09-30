"""Synthetic dataset generator components.

Component 1 (``DatasetConfig``) lives in ``..config`` and is the input every component
here receives.

Implemented:

* **Component 2 - Catalog Generator** (:mod:`.catalog`): the five master entities -
  ``Category``, ``Product``, ``Supplier``, ``ProductSupplier``, ``Location`` - plus
  ``manifest.json``.
* **Component 3 - Demand Generator** (:mod:`.demand`): ``demand.csv``, the **latent**
  demand history - product x location x day.
* **Component 4 - Inventory Simulator** (:mod:`.inventory`): ``consumption.csv``,
  ``inventory_movements.csv`` and ``inventory.csv``, plus the causal orders and receipts
  handed in memory to Component 5 (`DT-036`, `DT-038`).
* **Component 5 - Purchase Order Generator** (:mod:`.orders`): ``purchase_orders.csv``,
  ``purchase_order_items.csv`` and ``purchase_order_receipts.csv``, materialised from
  Component 4's ``SimulationResult`` without recomputing anything, plus ``order_number``
  and the synthetic ``CANCELLED`` twins (`DT-039`).
* **Component 6 - Supplier Behaviour Generator** (:mod:`.supplier_behaviour`): one
  deterministic ``SupplierProfile`` per supplier, in memory, for Component 4; no data
  file, only its entry in the manifest (`DT-037`).
* **W1 - publication** (:mod:`.pipeline`): one complete run C2 -> C3 -> C6 -> C4 -> C5 ->
  C7 -> C8 inside a workspace of its own, a final verification, and the promotion of the workspace
  to the output directory (`DT-040`). ``__main__`` runs it; no component is called from
  anywhere else.

The pipeline so far, and the distinction that carries it::

    C2 -> products.csv, locations.csv
       -> C3 -> demand.csv        latent demand: what would have been demanded
       -> C4 -> consumption.csv   satisfied demand: what stock allowed (`DT-034`)
             -> C5 -> purchase_orders.csv ...   the orders C4 decided, materialised

Supporting modules: :mod:`.rng` (determinism, `DT-030` / `DT-032`), :mod:`.policies`
(synthetic generation policies, `DT-028`, `DT-035`, `DT-036`, `DT-037` and `DT-039`),
:mod:`.writer` (output contract, `DT-024` / `DT-025` / `DT-033`).

* **Component 7 - Scenario Assignment** (:mod:`.scenarios`): records
  ``scenario_assignment`` in the manifest - the 16 Level A axes (`DT-041`).
* **Component 8 - Dataset Validator + quality report** (:mod:`.validator`): validates the
  materialised workspace with 51 checks and, only if all pass, records ``quality_report``
  in the manifest (`DT-042`).

W1 runs C2 -> C3 -> C6 -> C4 -> C5 -> C7 -> C8 -> verify -> promote (``generator_version``
0.4.0).
"""

from .catalog import Catalog, build_catalog, generate
from .demand import Demand, DemandProfile, build_demand
from .inventory import Inventory, SimulationResult, SupplierProfile, build_inventory
from .orders import Orders, build_orders
from .pipeline import run
from .policies import GeneratorError
from .supplier_behaviour import build_supplier_profiles

__all__ = [
    "Catalog",
    "build_catalog",
    "generate",
    "Demand",
    "DemandProfile",
    "build_demand",
    "Inventory",
    "SimulationResult",
    "SupplierProfile",
    "build_inventory",
    "Orders",
    "build_orders",
    "build_supplier_profiles",
    "run",
    "GeneratorError",
]
