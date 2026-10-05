// Recharts needs numbers to draw (DT-070 point 20: band chart). This is the only module where a figure
// of the API becomes a number, and only for the geometry of a chart: every figure shown as text (axis
// labels aside, tooltips, tables) keeps the exact text of the API. Nothing here feeds a decision.

/** Coordinate of a decimal text of the API; `NaN` for anything that is not a number. */
export function chartCoordinate(value: string): number {
  return Number(value);
}
