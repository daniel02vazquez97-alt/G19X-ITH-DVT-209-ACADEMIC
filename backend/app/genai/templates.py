"""Fixed texts of ``template/1.0.0`` (`docs/09` §14.5, `DT-068` point 7, `DT-069` point 5).

``string.Template`` from the standard library. ``$u`` is the product's ``unit_of_measure`` and
``$fuente`` the text of the lead-time source; every other placeholder is a fact key. No literal here
contains a digit, a ``%``, a date, a SKU, a version or a cardinal number written in words: the only
figures of a narrative come from ``Fact.display``. Changing any text that alters the narrative requires a
new ``GENERATOR`` version.
"""

from __future__ import annotations

import re
from string import Template

from .types import NO_NEED, RECOMMEND

UNIT_PLACEHOLDER = "u"
SOURCE_PLACEHOLDER = "fuente"
TEXT_PLACEHOLDERS = frozenset({UNIT_PLACEHOLDER, SOURCE_PLACEHOLDER})

MAIN: dict[str, Template] = {
    RECOMMEND: Template(
        "Se sugiere pedir $q_final $u. La posición de inventario para la decisión es de "
        "$inventory_position_decision $u: $on_hand en existencia, más $effective_in_transit en tránsito que "
        "llega dentro del horizonte, menos $reserved reservados. El nivel objetivo es de $target_level $u: la "
        "demanda prevista para los próximos $coverage_horizon_days días, de $demand_over_horizon $u, más un stock "
        "de seguridad de $safety_stock $u. Ese horizonte suma el plazo de entrega, de $lead_time_days días "
        "($fuente), y el periodo de revisión, de $review_period_days días. La necesidad bruta es de $raw_need $u."
    ),
    NO_NEED: Template(
        "No se sugiere pedido: la posición de inventario para la decisión, de "
        "$inventory_position_decision $u ($on_hand en existencia, más $effective_in_transit en tránsito que llega "
        "dentro del horizonte, menos $reserved reservados), cubre el nivel objetivo de $target_level $u. Ese nivel "
        "es la demanda prevista para los próximos $coverage_horizon_days días, de $demand_over_horizon $u, más un "
        "stock de seguridad de $safety_stock $u. El horizonte suma el plazo de entrega, de $lead_time_days días "
        "($fuente), y el periodo de revisión, de $review_period_days días."
    ),
}

#: One sentence per flag, in the canonical order of U1 (`docs/06` §16.11.4).
FLAG_SENTENCES: tuple[tuple[str, Template], ...] = (
    ("LEAD_TIME_AGREED_FALLBACK", Template(
        "No hay observaciones suficientes del plazo de entrega y se usa el acordado con el proveedor.")),
    ("LEAD_TIME_CAPPED", Template(
        "El plazo observado, de $uncapped_lead_time_days días, supera el máximo de la política y se limita a "
        "$lead_time_days días.")),
    ("MOQ_APPLIED", Template(
        "La necesidad es menor que el pedido mínimo del proveedor, de $moq $u, y se aplica ese mínimo.")),
    ("ORDER_MULTIPLE_ROUNDING", Template(
        "La cantidad se redondea hacia arriba al múltiplo de compra de $order_multiple $u, desde $q_moq $u.")),
    ("UNCOUNTED_TRANSIT", Template(
        "En total hay $total_in_transit $u en tránsito (posición contable de $inventory_position_accounting $u), "
        "pero solo $effective_in_transit $u llegan dentro del horizonte y cuentan para la decisión.")),
    ("OVERDUE_ORDERS_EXCLUDED", Template(
        "Hay pedidos abiertos con la fecha prevista ya vencida: no se cuentan como tránsito para la decisión.")),
    ("ZERO_FORECAST_DEMAND", Template(
        "No se prevé demanda en el horizonte: puede tratarse de un producto sin rotación.")),
)
FLAG_ORDER = tuple(flag for flag, _ in FLAG_SENTENCES)

LEAD_TIME_SOURCE_TEXTS = {
    "OBSERVED": "observado en las recepciones del proveedor",
    "AGREED_FALLBACK": "acordado con el proveedor",
}

#: Final sentence by the notices present (`DT-069` point 8); no sentence without notices.
PROVISIONAL_SENTENCES = {
    frozenset({"SYNTHETIC_DATA", "V1_PROVISIONAL_POLICY"}):
        "Aviso: las cifras son provisionales, calculadas con datos sintéticos y con la política provisional de la "
        "primera versión; no constituyen una recomendación de negocio definitiva.",
    frozenset({"SYNTHETIC_DATA"}):
        "Aviso: las cifras son provisionales, calculadas con datos sintéticos; no constituyen una recomendación de "
        "negocio definitiva.",
    frozenset({"V1_PROVISIONAL_POLICY"}):
        "Aviso: las cifras son provisionales, calculadas con la política provisional de la primera versión; no "
        "constituyen una recomendación de negocio definitiva.",
}
NOTICES = frozenset({"SYNTHETIC_DATA", "V1_PROVISIONAL_POLICY"})

#: ``reason_details`` of NOT_CALCULABLE, in the canonical order of U1 (`docs/06` §16.11.4).
REASON_TEXTS: tuple[tuple[str, str], ...] = (
    ("PRODUCT_INACTIVE", "El producto está inactivo."),
    ("PRODUCT_OUT_OF_VALIDITY",
     "El producto no es válido durante todo el periodo requerido, desde la fecha de corte hasta el final del "
     "horizonte."),
    ("NO_ACTIVE_PREFERRED_SUPPLIER", "El producto no tiene un proveedor preferente activo."),
    ("NEGATIVE_ON_HAND", "La existencia registrada es negativa: es un incidente de datos."),
    ("FORECAST_MISSING", "No hay pronóstico del producto en la ejecución de forecast utilizada."),
    ("FORECAST_TOO_SHORT", "El pronóstico no cubre todo el horizonte requerido."),
    ("INSUFFICIENT_HISTORY", "No hay historial de consumo suficiente para estimar la variabilidad de la demanda."),
    ("MISSING_POLICY_PARAMETER",
     "Faltan parámetros de la política de inventario: se enumeran en missing_policy_parameters."),
)
REASON_ORDER = tuple(code for code, _ in REASON_TEXTS)

# --- neighbourhood rules (`DT-069` point 5) ---------------------------------------------------------

_PLACEHOLDER = re.compile(r"\$(?:(?P<named>[_a-z][_a-z0-9]*)|\{(?P<braced>[_a-z][_a-z0-9]*)\})", re.IGNORECASE)
CARDINAL_WORDS = ("cero", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once",
                  "doce", "quince", "veinte", "treinta", "cien", "ciento", "mil", "millón", "millones")


def literal_violations(text: str) -> list[str]:
    """Problems of a literal text: digits, ``%`` or cardinal number words."""
    problems = []
    if re.search(r"\d", _PLACEHOLDER.sub("", text)):
        problems.append("digit in literal text")
    if "%" in text:
        problems.append("percent sign")
    for word in CARDINAL_WORDS:
        if re.search(rf"\b{word}\b", text, re.IGNORECASE):
            problems.append(f"number word {word!r}")
    return problems


def placeholder_violations(template: Template) -> list[str]:
    """Neighbourhood rules: left of a numeric placeholder no digit, ``.``, ``-`` or another placeholder;
    right of it no digit or another placeholder, and a ``.`` only followed by a space or the end."""
    text = template.template
    problems = []
    matches = list(_PLACEHOLDER.finditer(text))
    for index, match in enumerate(matches):
        name = match.group("named") or match.group("braced")
        if name in TEXT_PLACEHOLDERS:
            continue
        start, end = match.span()
        before = text[start - 1] if start else ""
        after = text[end] if end < len(text) else ""
        if before and (before.isdigit() or before in ".-"):
            problems.append(f"${name}: {before!r} before")
        if index and matches[index - 1].end() == start:
            problems.append(f"${name}: placeholder before")
        if after and (after.isdigit() or after == "$"):
            problems.append(f"${name}: {after!r} after")
        if after == "." and end + 1 < len(text) and not text[end + 1].isspace():
            problems.append(f"${name}: '.' followed by {text[end + 1]!r}")
    return problems


def placeholders(template: Template) -> set[str]:
    return {m.group("named") or m.group("braced") for m in _PLACEHOLDER.finditer(template.template)}


def all_texts() -> list[tuple[str, str]]:
    """Every fixed text with a name, for the static checks."""
    texts = [(f"main:{k}", t.template) for k, t in MAIN.items()]
    texts += [(f"flag:{k}", t.template) for k, t in FLAG_SENTENCES]
    texts += [(f"source:{k}", v) for k, v in LEAD_TIME_SOURCE_TEXTS.items()]
    texts += [(f"provisional:{'+'.join(sorted(k))}", v) for k, v in PROVISIONAL_SENTENCES.items()]
    texts += [(f"reason:{k}", v) for k, v in REASON_TEXTS]
    return texts


def all_templates() -> list[tuple[str, Template]]:
    return [(f"main:{k}", t) for k, t in MAIN.items()] + [(f"flag:{k}", t) for k, t in FLAG_SENTENCES]
