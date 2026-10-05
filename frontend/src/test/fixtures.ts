// API V1 bodies for the view tests, shaped like the real responses of the dataset 0.4.0 run
// (`backend/tests/genai/_genai_fixtures.py`). Quantities are text, as the API sends them.
import type { InventoryDetail, InventoryPage, ProductDetail, ProductPage } from '../api/types';

export const PRODUCT_4 = {
  id: 4,
  sku: 'SKU-00004',
  name: 'Product SKU-00004',
  category: { id: 2, code: 'CAT-02', name: 'Category 02' },
  unit_of_measure: 'BOX',
  is_active: true,
  valid_from: '2023-01-01',
  valid_to: null,
  data_origin: 'SYNTHETIC',
};

export const PRODUCT_PAGE: ProductPage = {
  items: [
    PRODUCT_4,
    {
      ...PRODUCT_4,
      id: 5,
      sku: 'SKU-00005',
      name: 'Product SKU-00005',
      unit_of_measure: 'KG',
      is_active: false,
      valid_to: '2025-06-30',
    },
  ],
  total: 120,
  page: 1,
  page_size: 50,
};

export const PRODUCT_4_DETAIL: ProductDetail = {
  ...PRODUCT_4,
  inventory: {
    on_hand: '242',
    reserved: '0',
    in_transit_total: '2623.500600092591729239380374',
    last_movement_at: '2026-01-01T03:30:00Z',
  },
  suppliers: [
    {
      supplier: { id: 10, code: 'SUP-010', name: 'Supplier SUP-010' },
      moq: '1',
      order_multiple: '100',
      unit_cost: '12.500000',
      agreed_lead_time_days: 21,
      is_preferred: true,
      is_active: true,
    },
  ],
};

export const INVENTORY_PAGE: InventoryPage = {
  items: [
    {
      product_id: 4,
      sku: 'SKU-00004',
      on_hand: '242',
      reserved: '0',
      available: '242',
      in_transit_total: '0',
      inventory_position_accounting: '242.000000',
      last_movement_at: '2025-12-30T18:00:00Z',
      data_origin: 'SYNTHETIC',
    },
  ],
  total: 1,
  page: 1,
  page_size: 50,
};

export const INVENTORY_46: InventoryDetail = {
  product_id: 46,
  sku: 'SKU-00046',
  on_hand: '39',
  reserved: '0',
  available: '39',
  in_transit_total: '90',
  inventory_position_accounting: '129',
  last_movement_at: null,
  data_origin: 'SYNTHETIC',
  open_lines: [
    {
      order_number: 'PO-003561',
      supplier: { id: 1, code: 'SUP-001', name: 'Supplier SUP-001' },
      status: 'ISSUED',
      expected_on: '2026-01-20',
      quantity_pending: '45',
    },
  ],
};

export const PRODUCT_46_DETAIL: ProductDetail = {
  ...PRODUCT_4_DETAIL,
  id: 46,
  sku: 'SKU-00046',
  name: 'Product SKU-00046',
  unit_of_measure: 'KG',
};
