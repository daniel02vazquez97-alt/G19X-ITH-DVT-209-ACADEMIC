// Filters by the codes the interface shows (DT-105): SKU, category and supplier codes. The API matches them
// exactly, without case; an unknown code gives an empty page. The internal identifiers are never asked for.
import type { FilterField } from './FilterForm';

export const SKU_FILTER: FilterField = {
  key: 'sku',
  label: 'Producto (SKU)',
  kind: 'text',
  help: 'Ejemplo: SKU-00004',
};

export const CATEGORY_FILTER: FilterField = {
  key: 'category_code',
  label: 'Categoría (código)',
  kind: 'text',
  help: 'Ejemplo: CAT-001',
};

export const SUPPLIER_FILTER: FilterField = {
  key: 'supplier_code',
  label: 'Proveedor (código)',
  kind: 'text',
  help: 'Ejemplo: SUP-010',
};

export const RUN_FILTER: FilterField = {
  key: 'run_id',
  label: 'Ejecución (número)',
  kind: 'id',
  help: 'El número de «Ejecución #2». Vacío: la última completada.',
};
