"""Closed-loop Level 2 simulation of every branch (`DT-080`, OD-S1 to OD-S4 accepted in `DT-088`).

For each product with ``L + R`` (an active preferred supplier) and valid at the first cut (`DT-087`):

1. **Initial state** at the close of the first cut: ``on_hand`` from ``inventory_movements``, ``reserved = 0``,
   the real lines open at that date as exogenous events (identical in every branch) and the real lead-time
   observations of orders issued up to the first cut. Real orders issued later are discarded.
2. **Every day** until 2025-09-24 (`environment.simulate_day`): receipts, latent demand, consumption, lost sales.
3. **Every 7 days**, after the consumption of the day: the branch forecast on its own simulated history,
   then U1 ``evaluate`` (unchanged, same ``engine_version`` in every branch). A ``RECOMMEND`` places an order on
   that date (``suggested_order_date``, as U4) for ``q_final`` units that arrives ``lead_time_days`` later
   (the ``L`` the engine used); it counts as transit in the following decisions. No cancellations or
   partial deliveries.

Only the forecast changes between branches. The orders of a branch never use the real supplier
variability: the simulation isolates the effect of the forecast (stated in the report).
"""

from __future__ import annotations

import datetime as _dt
from collections import defaultdict
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass, field
from decimal import Context, Decimal
from fractions import Fraction
from pathlib import Path

from app.supply_engine import (
    ENGINE_VERSION,
    V1_PROVISIONAL_PARAMETERS,
    EvaluationResult,
    LeadTimeObservation,
    MethodUsed,
    Outcome,
    PolicyParameters,
    evaluate,
)
from app.supply_engine import rules

from ..config import F5aConfig
from ..cuts import LAST_READABLE_DATE, check_readable, development_cuts
from ..data import Dataset, ExogenousLine, SeriesKey, load_dataset, on_hand_at, open_lines_at, preferred_unit_costs
from ..models import MODEL_NAMES, SES_NAME
from .engine_inputs import LineState, evaluation_input
from .environment import LatentDemand, load_latent_demand, simulate_day
from .forecasters import WeeklyHistory, point_forecast

#: Exogenous open lines arrive on their ``expected_on`` (`DT-080` point 7, ACEPTADA); overdue lines arrive the
#: day after the first cut (provisional reading: the literal rule gives them no date).
OPEN_LINES_EXPECTED_ON = "EXPECTED_ON"
#: Alternative of OD-S1 («llegadas reales»): the real receipts after the first cut, up to the readable limit.
OPEN_LINES_ACTUAL_RECEIPTS = "ACTUAL_RECEIPTS"

#: Identifier base of the simulated orders (never collides with a real purchase order).
SIMULATED_ORDER_BASE = 1_000_000_000
NOT_VALID_AT_FIRST_CUT = "NOT_VALID_AT_FIRST_CUT"
NO_ACTIVE_PREFERRED_SUPPLIER = "NO_ACTIVE_PREFERRED_SUPPLIER"

_ONE_DAY = _dt.timedelta(days=1)
_EXACT = Context(prec=60)


@dataclass(frozen=True)
class SimConfig:
    """Configuration of one F5b run; provisional values are labelled in the report."""

    first_cut: _dt.date = field(default_factory=lambda: development_cuts()[0])
    period_end: _dt.date = LAST_READABLE_DATE
    #: Weekly decisions (`DT-080` point 2); must equal the ``R`` of the U1 policy.
    review_days: int = 7
    #: Forecast recomputed every N weekly decisions (provisional; 1 = every decision).
    retrain_every_weeks: int = 1
    #: Warm-up excluded from the second reporting period (provisional).
    warmup_weeks: int = 8
    open_lines_rule: str = OPEN_LINES_EXPECTED_ON
    branches: tuple[str, ...] = MODEL_NAMES
    f5a: F5aConfig = field(default_factory=F5aConfig)
    policy: PolicyParameters = V1_PROVISIONAL_PARAMETERS

    def __post_init__(self) -> None:
        check_readable(self.period_end)
        if self.review_days != self.policy.r:
            raise ValueError("the review period must equal the R of the U1 policy")
        if self.retrain_every_weeks < 1 or self.warmup_weeks < 0:
            raise ValueError("invalid cadence or warm-up")
        if self.open_lines_rule not in (OPEN_LINES_EXPECTED_ON, OPEN_LINES_ACTUAL_RECEIPTS):
            raise ValueError(f"unknown open-lines rule {self.open_lines_rule}")

    def decision_days(self) -> list[_dt.date]:
        days, day = [], self.first_cut
        while day < self.period_end:
            days.append(day)
            day += _ONE_DAY * self.review_days
        return days

    def describe(self) -> dict:
        return {
            "label": "PROPUESTA (provisional) where marked",
            "first_cut": self.first_cut.isoformat(),
            "period_end": self.period_end.isoformat(),
            "review_days": self.review_days,
            "retrain_every_weeks": {"value": self.retrain_every_weeks, "status": "provisional"},
            "warmup_weeks": {"value": self.warmup_weeks, "status": "provisional"},
            "open_lines_rule": {
                "value": self.open_lines_rule,
                "status": "DT-080 point 7 by default; ACTUAL_RECEIPTS pending the responsable (OD-S1)",
            },
            "branches": list(self.branches),
            "population": "validity on the first cut (DT-087) and an active preferred supplier (L + R)",
            "lead_time_observations": "real lines issued up to the first cut; U1 keeps those completed by each decision",
            "u1": {"engine_version": ENGINE_VERSION, "policy": {k: str(v) for k, v in asdict(self.policy).items()}},
            "f5a_models": self.f5a.describe(),
        }


@dataclass(frozen=True)
class SimulationInputs:
    dataset: Dataset
    demand: LatentDemand
    on_hand: dict[SeriesKey, Decimal]
    open_lines: tuple[ExogenousLine, ...]
    observations: tuple[LeadTimeObservation, ...]
    unit_costs: dict[int, Decimal]


def prepare_inputs(directory: Path | str, config: SimConfig) -> SimulationInputs:
    """Everything the simulation reads, up to the readable limit (`DT-075` point 4)."""
    dataset = load_dataset(directory)
    return SimulationInputs(
        dataset=dataset,
        demand=load_latent_demand(directory, dataset.data_origin),
        on_hand=on_hand_at(directory, config.first_cut),
        open_lines=open_lines_at(directory, config.first_cut),
        observations=tuple(o for o in dataset.lead_time_observations if o.issued_on <= config.first_cut),
        unit_costs=preferred_unit_costs(directory),
    )


@dataclass(frozen=True, slots=True)
class SimulatedOrder:
    branch: str
    order_id: int
    placed_on: _dt.date
    quantity: Decimal
    lead_time_days: int
    arrival_on: _dt.date


@dataclass(frozen=True, slots=True)
class Decision:
    day: _dt.date
    outcome: str
    reasons: tuple[str, ...]
    engine_version: str
    forecast_available: bool


@dataclass
class BranchTrace:
    """Daily trajectory of one branch for one product; index 0 is the day after the first cut."""

    received: list[Decimal] = field(default_factory=list)
    consumption: list[Decimal] = field(default_factory=list)
    lost: list[Decimal] = field(default_factory=list)
    end_on_hand: list[Decimal] = field(default_factory=list)
    orders: list[SimulatedOrder] = field(default_factory=list)
    decisions: list[Decision] = field(default_factory=list)
    #: Snapshot of the U1 inputs, only when ``keep_inputs`` (tests).
    inputs: list = field(default_factory=list)


@dataclass
class ProductSimulation:
    key: SeriesKey
    start: _dt.date
    demand: list[Decimal]
    initial_on_hand: Decimal
    exogenous: tuple[ExogenousLine, ...]
    traces: dict[str, BranchTrace]


@dataclass
class SimulationResult:
    config: SimConfig
    products: list[ProductSimulation]
    excluded: list[dict]


def fraction_to_decimal(value: Fraction) -> Decimal:
    """Exact conversion of an engine quantity (``q_final`` is a multiple of a decimal order multiple)."""
    result = _EXACT.divide(Decimal(value.numerator), Decimal(value.denominator))
    if Fraction(result) != value:
        raise ValueError(f"{value} has no exact decimal representation")
    return result


def _exogenous_arrivals(lines: Sequence[ExogenousLine], config: SimConfig) -> dict[_dt.date, list[tuple[int, Decimal]]]:
    """``day → [(line index, quantity)]`` under the configured rule."""
    arrivals: dict[_dt.date, list[tuple[int, Decimal]]] = defaultdict(list)
    first_day = config.first_cut + _ONE_DAY
    for index, line in enumerate(lines):
        if config.open_lines_rule == OPEN_LINES_EXPECTED_ON:
            day = max(line.expected_on, first_day)
            if day <= config.period_end:
                arrivals[day].append((index, line.pending_at_cut))
        else:
            for day, quantity in line.receipts_after:
                if day <= config.period_end:
                    arrivals[day].append((index, quantity))
    return arrivals


Forecaster = Callable[[str, WeeklyHistory, F5aConfig], "tuple[Decimal, ...] | None"]


def simulate_product(
    inputs: SimulationInputs,
    key: SeriesKey,
    config: SimConfig,
    forecaster: Forecaster = point_forecast,
    keep_inputs: bool = False,
) -> ProductSimulation:
    """All branches of one product: identical environment and exogenous events, own history and inventory."""
    ds = inputs.dataset
    product_id, location_id = key
    product = ds.products[product_id]
    relations = ds.relations.get(product_id, ())
    observed = ds.history(key, config.first_cut)
    if not observed:
        raise ValueError(f"{key}: no observed history up to the first cut")
    history_start = observed[0].day
    observed_qty = [row.quantity for row in observed]
    base_weeks = WeeklyHistory(observed_qty)
    lines = tuple(line for line in inputs.open_lines if (line.product_id, line.location_id) == key)
    arrivals = _exogenous_arrivals(lines, config)
    days = (config.period_end - config.first_cut).days
    demand = [inputs.demand.on(key, config.first_cut + _ONE_DAY * (i + 1)) for i in range(days)]
    initial = inputs.on_hand.get(key, Decimal(0))
    if initial < 0:
        raise ValueError(f"{key}: negative on_hand at the first cut")
    decision_days = set(config.decision_days())
    traces = {}
    for branch_index, branch in enumerate(config.branches):
        trace = BranchTrace()
        on_hand = initial
        history = list(observed_qty)
        weeks = WeeklyHistory([])
        weeks.weeks, weeks.floats = list(base_weeks.weeks), list(base_weeks.floats)
        exo_pending = [line.pending_at_cut for line in lines]
        orders: list[SimulatedOrder] = []
        points: tuple[Decimal, ...] | None = None
        decisions_done = 0

        def decide(day: _dt.date) -> None:
            nonlocal points, decisions_done, on_hand
            if decisions_done % config.retrain_every_weeks == 0:
                points = forecaster(branch, weeks, config.f5a)
            decisions_done += 1
            open_lines = [
                LineState(line.purchase_order_id, line.item_id, line.supplier_id, line.expected_on, exo_pending[i])
                for i, line in enumerate(lines)
            ] + [
                LineState(o.order_id, 1, rules.select_supplier(relations).supplier_id, o.arrival_on, o.quantity)
                for o in orders
                if o.arrival_on > day
            ]
            engine_input = evaluation_input(
                as_of=day,
                product=product,
                location_id=location_id,
                relations=relations,
                on_hand=on_hand,
                lines=open_lines,
                observations=inputs.observations,
                consumption_start=history_start,
                consumption=history,
                forecast_points=points,
                forecast_id=decisions_done,
                model_version=branch_index + 1,
                method_used=MethodUsed.MODEL if branch == SES_NAME else MethodUsed.BASELINE,
                policy=config.policy,
            )
            if keep_inputs:
                trace.inputs.append(engine_input)
            result: EvaluationResult = evaluate(engine_input)
            trace.decisions.append(
                Decision(
                    day,
                    str(result.outcome.value),
                    tuple(str(r.value) for r in result.reasons),
                    result.engine_version,
                    points is not None,
                )
            )
            if result.outcome is Outcome.RECOMMEND:
                b = result.breakdown
                assert b.q_final is not None and b.lead_time_days is not None
                order = SimulatedOrder(
                    branch=branch,
                    order_id=SIMULATED_ORDER_BASE + len(orders) + 1,
                    placed_on=day,
                    quantity=fraction_to_decimal(b.q_final),
                    lead_time_days=b.lead_time_days,
                    arrival_on=day + _ONE_DAY * b.lead_time_days,
                )
                orders.append(order)
                trace.orders.append(order)
                if order.lead_time_days == 0:  # arrives the same day, after the decision
                    on_hand += order.quantity
                    if trace.end_on_hand:
                        trace.received[-1] += order.quantity
                        trace.end_on_hand[-1] = on_hand

        decide(config.first_cut)
        for i in range(days):
            day = config.first_cut + _ONE_DAY * (i + 1)
            received = Decimal(0)
            for index, quantity in arrivals.get(day, ()):
                received += quantity
                exo_pending[index] = max(exo_pending[index] - quantity, Decimal(0))
            for order in orders:
                if order.arrival_on == day and order.lead_time_days > 0:
                    received += order.quantity
            out = simulate_day(on_hand, received, demand[i])
            on_hand = out.end_on_hand
            trace.received.append(out.received)
            trace.consumption.append(out.consumption)
            trace.lost.append(out.lost)
            trace.end_on_hand.append(out.end_on_hand)
            if product.valid_to is None or day <= product.valid_to:
                history.append(out.consumption)
            if day in decision_days:
                if product.valid_to is None or day <= product.valid_to:
                    weeks.append_week(history[-7:])
                decide(day)
        traces[branch] = trace
    return ProductSimulation(key, config.first_cut + _ONE_DAY, demand, initial, lines, traces)


def eligible_keys(ds: Dataset, config: SimConfig) -> tuple[list[SeriesKey], list[dict]]:
    """Population of `DT-087` at the first cut with ``L + R``; the others are counted and listed."""
    keep, excluded = [], []
    for key in ds.series_keys():
        product = ds.products[key[0]]
        if not product.valid_on(config.first_cut):
            excluded.append({"product_id": key[0], "location_id": key[1], "reason": NOT_VALID_AT_FIRST_CUT})
        elif rules.select_supplier(ds.relations.get(key[0], ())) is None:
            excluded.append({"product_id": key[0], "location_id": key[1], "reason": NO_ACTIVE_PREFERRED_SUPPLIER})
        else:
            keep.append(key)
    return keep, excluded


def run_simulation(
    inputs: SimulationInputs,
    config: SimConfig,
    products: Sequence[int] | None = None,
    forecaster: Forecaster = point_forecast,
) -> SimulationResult:
    keys, excluded = eligible_keys(inputs.dataset, config)
    if products is not None:
        wanted = set(products)
        keys = [k for k in keys if k[0] in wanted]
        excluded = [e for e in excluded if e["product_id"] in wanted]
    return SimulationResult(config, [simulate_product(inputs, key, config, forecaster) for key in keys], excluded)
