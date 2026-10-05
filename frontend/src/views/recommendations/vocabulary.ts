// Wording of the engine codes in the interface. Only presentation: the codes come from the API and
// stay visible next to their text.

export const OUTCOME_LABELS: Record<string, string> = {
  RECOMMEND: 'Se sugiere pedir',
  NO_NEED: 'Sin necesidad de pedido',
  NOT_CALCULABLE: 'No calculable',
};

export function outcomeLabel(outcome: string): string {
  return OUTCOME_LABELS[outcome] ?? outcome;
}

/** Names of the `facts[]` keys of U6 (`app.genai.facts.VOCABULARY`, DT-068 point 5). */
export const FACT_LABELS: Record<string, string> = {
  q_final: 'Cantidad sugerida',
  raw_need: 'Necesidad bruta',
  safety_stock: 'Stock de seguridad',
  target_level: 'Nivel objetivo',
  lead_time_days: 'Plazo de entrega',
  uncapped_lead_time_days: 'Plazo de entrega antes del tope',
  review_period_days: 'Periodo de revisión',
  coverage_horizon_days: 'Horizonte de la decisión',
  demand_over_horizon: 'Demanda prevista en el horizonte',
  inventory_position_decision: 'Posición de inventario para la decisión',
  inventory_position_accounting: 'Posición contable',
  total_in_transit: 'En tránsito (total)',
  effective_in_transit: 'En tránsito que llega dentro del horizonte',
  moq: 'Pedido mínimo',
  order_multiple: 'Múltiplo de compra',
  q_moq: 'Cantidad tras el pedido mínimo',
  on_hand: 'Existencia',
  reserved: 'Reservado',
};

export function factLabel(key: string): string {
  return FACT_LABELS[key] ?? key;
}

/** Unit text of a fact: `QUANTITY` is the unit of measure of the product. */
export function factUnit(unit: string, unitOfMeasure: string | null): string {
  if (unit === 'QUANTITY') {
    return unitOfMeasure ?? '';
  }
  if (unit === 'DAYS') {
    return 'días';
  }
  return '';
}
