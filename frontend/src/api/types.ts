// Contract types of the API V1. They come from the generated OpenAPI (`npm run gen:api`, DT-070
// point 8); quantities are `Decimal` serialized as JSON strings and stay `string` here. Integer
// identifiers and pagination counters are JSON integers in the contract and stay `number`.
import type { components } from './schema.gen';

type Schemas = components['schemas'];

export type Me = Schemas['Me'];
export type ErrorResponse = Schemas['ErrorResponse'];
export type Product = Schemas['Product'];
export type ProductPage = Schemas['ProductPage'];
export type ProductDetail = Schemas['ProductDetail'];
export type InventoryItem = Schemas['InventoryItem'];
export type InventoryPage = Schemas['InventoryPage'];
export type InventoryDetail = Schemas['InventoryDetail'];
export type History = Schemas['History'];
export type ForecastPage = Schemas['ForecastPage'];
export type ProductForecast = Schemas['ProductForecast'];
export type RecommendationItem = Schemas['RecommendationItem'];
export type RecommendationPage = Schemas['RecommendationPage'];
export type RunDetail = Schemas['RunDetail'];
export type RecommendationExplanation = Schemas['RecommendationExplanation'];
export type ForecastProvenance = Schemas['ForecastProvenance'];
export type RecommendationProvenance = Schemas['RecommendationProvenance'];
export type Notice = RecommendationProvenance['notices'][number];

/**
 * Exact value of the engine as U4 stored it (DT-059, `docs/06` §16.13.3): an integer, a finite
 * decimal, a 28-digit approximate `Decimal` or a rational `"p/q"`. Always text; never a float.
 */
export type ExactValue = string;

/** One open line counted as effective transit, as stored in the breakdown. */
export interface EffectiveLine {
  item_id: string;
  purchase_order_id: string;
  supplier_id: string;
  expected_on: string;
  quantity_pending: ExactValue;
}

/** Forecast block of `calculation_inputs` (`backend/app/runs/recommendation.py`), or `null`. */
export interface CalculationForecast {
  forecast_run_id: string;
  forecast_id: string;
  model: { name: string; version: string } | null;
  method_used: string;
  confidence_flag: string;
  start_date: string;
  weekly_quantities: ExactValue[];
}

/**
 * `calculation_inputs` of a recommendation. The OpenAPI declares it as a free object
 * (`dict[str, Any]`), so it is typed by hand from the persisted document (DT-059).
 */
export interface CalculationInputs {
  breakdown: Record<string, ExactValue | EffectiveLine[] | null>;
  approximate_terms: string[];
  forecast: CalculationForecast | null;
  input_sha256: string;
}

export type RecommendationDetail = Omit<Schemas['RecommendationDetail'], 'calculation_inputs'> & {
  calculation_inputs: CalculationInputs;
};
