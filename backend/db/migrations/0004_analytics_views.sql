-- 0004 — Capa analítica de solo lectura (U9, DT-097; docs/11 §2, §3 y §9; docs/10 §7).
--
-- Vistas en el esquema `analytics`, separado de las tablas operativas de `public`, y el rol
-- `analytics_reader` (sin LOGIN): USAGE sobre `analytics` y SELECT sobre sus vistas, nada más. Las vistas
-- se ejecutan con los privilegios de su propietario (el usuario de migraciones), así que el rol no
-- recibe ningún permiso sobre las tablas. Solo se exponen hechos y valores ya calculados; ningún KPI
-- depende de parámetros de negocio inexistentes (BR-X03, valoración del inventario: docs/11 §9).
-- Instantes convertidos a fecha en UTC (docs/04 §9.7). Sin tablas nuevas ni vistas materializadas:
-- las tablas operativas, U2–U6 y sus consultas no cambian.

CREATE SCHEMA analytics;

-- Carga vigente: la única COMPLETED de la base (DT-044). El corte es su último día (DT-058).
CREATE VIEW analytics.data_load AS
SELECT id                       AS data_load_id,
       dataset_version,
       generator_version,
       data_origin,
       lower(time_range)        AS period_start,
       upper(time_range) - 1    AS cut_date,
       finished_at              AS loaded_at
FROM data_loads
WHERE status = 'COMPLETED';

-- Calendario natural desde el primer día cargado hasta el último día con forecast. Sin día hábil ni
-- festivos: el calendario del negocio está pendiente (docs/11 §3.1, BR-X06).
CREATE VIEW analytics.dim_date AS
WITH bounds AS (
    SELECT min(first_day) AS first_day, max(last_day) AS last_day
    FROM (
        SELECT period_start AS first_day, cut_date AS last_day FROM analytics.data_load
        UNION ALL
        SELECT NULL, max(f.period_end) - 1
        FROM forecasts f JOIN calculation_runs r ON r.id = f.calculation_run_id
        WHERE r.status = 'COMPLETED'
    ) b
)
SELECT d::date                          AS calendar_date,
       extract(year FROM d)::integer    AS year,
       extract(quarter FROM d)::integer AS quarter,
       extract(month FROM d)::integer   AS month,
       extract(day FROM d)::integer     AS day_of_month,
       extract(isoyear FROM d)::integer AS iso_year,
       extract(week FROM d)::integer    AS iso_week,
       extract(isodow FROM d)::integer  AS iso_day_of_week
FROM bounds, generate_series(bounds.first_day, bounds.last_day, interval '1 day') AS d;

CREATE VIEW analytics.dim_product AS
SELECT id AS product_id, sku, name, category_id, unit_of_measure, abc_class, rotation_class,
       is_active, valid_from, valid_to, data_origin
FROM products;

CREATE VIEW analytics.dim_category AS
SELECT id AS category_id, code, name, parent_id, is_active, data_origin
FROM categories;

-- Sin datos de contacto: no los necesita ningún KPI.
CREATE VIEW analytics.dim_supplier AS
SELECT id AS supplier_id, code, name, currency, is_active, data_origin
FROM suppliers;

CREATE VIEW analytics.dim_location AS
SELECT id AS location_id, code, name, type, is_active, data_origin
FROM locations;

CREATE VIEW analytics.dim_model_version AS
SELECT id AS model_version_id, name, version, algorithm, is_baseline, status
FROM model_versions;

-- Producto × ubicación × día. La demanda latente solo existe en datos sintéticos (docs/04 §3.7-bis):
-- con ella se calcula la tasa de satisfacción alcanzada, nunca con datos REAL.
CREATE VIEW analytics.fact_consumption AS
SELECT c.product_id,
       c.location_id,
       c.occurred_on,
       c.quantity              AS consumed_quantity,
       c.is_stockout_affected,
       d.quantity              AS latent_demand_quantity,
       c.data_origin
FROM consumption c
LEFT JOIN demand d
       ON d.product_id = c.product_id AND d.location_id = c.location_id AND d.occurred_on = c.occurred_on;

-- Producto × ubicación al corte. Posición contable = existencia + tránsito total − comprometido
-- (DT-012, docs/06 §4.2); la posición de decisión, con el tránsito efectivo, vive en el motor.
CREATE VIEW analytics.fact_inventory_current AS
SELECT i.product_id,
       i.location_id,
       l.cut_date                                                        AS as_of_date,
       i.quantity_on_hand,
       i.quantity_reserved,
       i.quantity_in_transit,
       i.quantity_on_hand + i.quantity_in_transit - i.quantity_reserved AS accounting_position,
       i.last_movement_at,
       i.data_origin
FROM inventory i
CROSS JOIN analytics.data_load l;

-- Producto × ubicación × día del periodo cargado: existencia al cierre del día (UTC) reconstruida como
-- la suma acumulada de los movimientos, la misma regla con la que la ingesta reconcilia `inventory`
-- (docs/04 §9.9); los movimientos anteriores al periodo, si los hubiera, forman el saldo inicial. El
-- último día coincide con quantity_on_hand de fact_inventory_current.
CREATE VIEW analytics.fact_inventory_daily AS
WITH dl AS (
    SELECT period_start, cut_date FROM analytics.data_load
),
movement AS (
    SELECT m.product_id, m.location_id, (m.occurred_at AT TIME ZONE 'UTC')::date AS movement_on, m.quantity
    FROM inventory_movements m
),
opening AS (
    SELECT movement.product_id, movement.location_id, sum(movement.quantity) AS quantity
    FROM movement CROSS JOIN dl
    WHERE movement.movement_on < dl.period_start
    GROUP BY movement.product_id, movement.location_id
),
grid AS (
    -- Un día por par de inventario y por fecha del periodo, más los movimientos de ese día.
    SELECT product_id, location_id, calendar_date, sum(quantity) AS net_movement_quantity
    FROM (
        SELECT i.product_id, i.location_id, dl.period_start + g.n AS calendar_date, 0::numeric AS quantity
        FROM inventory i
        CROSS JOIN dl
        CROSS JOIN generate_series(0, dl.cut_date - dl.period_start) AS g (n)
        UNION ALL
        SELECT movement.product_id, movement.location_id, movement.movement_on, movement.quantity
        FROM movement CROSS JOIN dl
        WHERE movement.movement_on BETWEEN dl.period_start AND dl.cut_date
          AND EXISTS (SELECT 1 FROM inventory i
                      WHERE i.product_id = movement.product_id AND i.location_id = movement.location_id)
    ) u
    GROUP BY product_id, location_id, calendar_date
)
SELECT grid.product_id,
       grid.location_id,
       grid.calendar_date,
       grid.net_movement_quantity,
       coalesce(opening.quantity, 0)
         + sum(grid.net_movement_quantity) OVER (
               PARTITION BY grid.product_id, grid.location_id ORDER BY grid.calendar_date
           ) AS on_hand_end_of_day
FROM grid
LEFT JOIN opening ON opening.product_id = grid.product_id AND opening.location_id = grid.location_id;

-- Línea de orden de compra. Mismas lecturas que U4 (docs/04 §9.11, runs/recommendation_inputs.py):
-- - fecha esperada = la de la línea o, si es nula, la de la cabecera;
-- - abierta = cabecera ISSUED o PARTIALLY_RECEIVED con pendiente > 0;
-- - observación de lead time = línea completamente recibida (recibido = pedido, al menos una
--   recepción), fechada por su última recepción (DT-031 V1-09, knowledge/glossary.md).
CREATE VIEW analytics.fact_purchase_order_line AS
WITH receipts AS (
    SELECT purchase_order_item_id, max(received_at) AS last_received_at, count(*) AS receipt_count
    FROM purchase_order_receipts
    GROUP BY purchase_order_item_id
),
line AS (
    SELECT i.id                                                              AS purchase_order_item_id,
           po.id                                                             AS purchase_order_id,
           po.order_number,
           i.product_id,
           po.supplier_id,
           po.location_id,
           po.status                                                         AS order_status,
           po.currency,
           (po.issued_at AT TIME ZONE 'UTC')::date                           AS issued_on,
           (coalesce(i.expected_at, po.expected_at) AT TIME ZONE 'UTC')::date AS expected_on,
           (po.closed_at AT TIME ZONE 'UTC')::date                           AS closed_on,
           i.quantity_ordered,
           i.quantity_received,
           CASE WHEN po.status IN ('ISSUED', 'PARTIALLY_RECEIVED')
                THEN i.quantity_ordered - i.quantity_received ELSE 0 END     AS quantity_pending,
           i.unit_cost,
           ps.agreed_lead_time_days,
           (r.last_received_at AT TIME ZONE 'UTC')::date                     AS last_received_on,
           coalesce(r.receipt_count, 0)                                      AS receipt_count,
           (i.quantity_received = i.quantity_ordered AND r.last_received_at IS NOT NULL) AS is_fully_received,
           i.data_origin
    FROM purchase_order_items i
    JOIN purchase_orders po ON po.id = i.purchase_order_id
    LEFT JOIN receipts r ON r.purchase_order_item_id = i.id
    LEFT JOIN product_suppliers ps ON ps.product_id = i.product_id AND ps.supplier_id = po.supplier_id
)
SELECT line.purchase_order_item_id,
       line.purchase_order_id,
       line.order_number,
       line.product_id,
       line.supplier_id,
       line.location_id,
       line.order_status,
       line.currency,
       line.issued_on,
       line.expected_on,
       line.closed_on,
       line.quantity_ordered,
       line.quantity_received,
       line.quantity_pending,
       line.quantity_pending > 0                                                       AS is_open,
       line.unit_cost,
       line.agreed_lead_time_days,
       line.last_received_on,
       line.receipt_count,
       line.is_fully_received,
       CASE WHEN line.is_fully_received THEN line.last_received_on - line.issued_on END AS observed_lead_time_days,
       CASE WHEN line.is_fully_received THEN line.last_received_on <= line.expected_on END AS is_on_time,
       CASE WHEN line.quantity_pending > 0 THEN dl.cut_date - line.issued_on END      AS open_age_days_at_cut,
       line.data_origin
FROM line
LEFT JOIN analytics.data_load dl ON true;

-- Producto × ubicación × semana × corte × versión de modelo, de las ejecuciones COMPLETED (U3, DT-057).
CREATE VIEW analytics.fact_forecast AS
SELECT f.id AS forecast_id,
       f.calculation_run_id,
       f.as_of_date,
       f.product_id,
       f.location_id,
       f.model_version_id,
       f.period_start,
       f.period_end,
       f.granularity,
       f.predicted_quantity,
       f.lower_bound,
       f.upper_bound,
       f.confidence_level,
       f.method_used,
       f.confidence_flag,
       f.is_primary
FROM forecasts f
JOIN calculation_runs r ON r.id = f.calculation_run_id
WHERE r.status = 'COMPLETED';

-- Una evaluación del motor por ejecución × producto × ubicación (U4, DT-059). V1 no tiene estado ni
-- resolución humana: no hay «recomendaciones abiertas», conversión ni descarte (docs/11 §9).
CREATE VIEW analytics.fact_recommendation AS
SELECT rec.id                                          AS recommendation_id,
       rec.calculation_run_id,
       r.forecast_run_id,
       rec.as_of_date,
       rec.product_id,
       rec.location_id,
       rec.outcome,
       array_to_string(rec.reasons, ',')                AS reasons,
       array_to_string(rec.flags, ',')                  AS flags,
       array_to_string(rec.missing_policy_parameters, ',') AS missing_policy_parameters,
       rec.forecast_id,
       rec.suggested_supplier_id,
       rec.suggested_order_date,
       rec.recommended_quantity,
       rec.raw_quantity,
       rec.reorder_point,
       rec.safety_stock,
       rec.lead_time_used_days,
       rec.demand_during_lead_time,
       rec.inventory_position_at_calc,
       rec.policy_set,
       rec.engine_version,
       rec.generated_at
FROM recommendations rec
JOIN calculation_runs r ON r.id = rec.calculation_run_id
WHERE r.status = 'COMPLETED';

-- Rol de lectura analítica (docs/10 §7). Los roles son del clúster: se crea una sola vez y cada base
-- recibe sus permisos. Sin LOGIN ni contraseña: la cuenta que se conecte (Power BI, U16) se crea fuera
-- del repositorio, con su secreto en el almacén (DT-022), y se hace miembro de este rol.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'analytics_reader') THEN
        CREATE ROLE analytics_reader NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION NOBYPASSRLS;
    END IF;
    EXECUTE format('GRANT CONNECT ON DATABASE %I TO analytics_reader', current_database());
END
$$;

REVOKE ALL ON SCHEMA analytics FROM PUBLIC;
GRANT USAGE ON SCHEMA analytics TO analytics_reader;
GRANT SELECT ON ALL TABLES IN SCHEMA analytics TO analytics_reader;
-- Las vistas que añadan migraciones posteriores en `analytics` quedan legibles sin otro GRANT; nada
-- de `public` se concede.
ALTER DEFAULT PRIVILEGES IN SCHEMA analytics GRANT SELECT ON TABLES TO analytics_reader;
