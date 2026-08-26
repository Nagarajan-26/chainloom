-- ChainLoom
-- RAW refinement validation
-- Version: 1.2

USE DATABASE CHAINLOOM;
USE SCHEMA RAW;

-- 1. Production severity by affected product
SELECT
    product_id,
    COUNT(*) AS production_days,
    ROUND(AVG(planned_quantity - produced_quantity), 2) AS avg_production_gap,
    ROUND(AVG(downtime_hours), 2) AS avg_downtime_hours,
    SUM(IFF(production_status = 'Constrained', 1, 0)) AS constrained_days
FROM PRODUCTION
WHERE plant_id = 'PL03'
  AND production_date >= '2026-08-05'::DATE
  AND product_id IN ('PR202', 'PR203', 'PR204', 'PR206')
GROUP BY product_id
ORDER BY avg_production_gap DESC;

-- 2. Customer fulfillment by affected product
SELECT
    product_id,
    COUNT(*) AS order_lines,
    SUM(ordered_quantity) AS ordered_qty,
    SUM(fulfilled_quantity) AS fulfilled_qty,
    SUM(ordered_quantity - fulfilled_quantity) AS unfulfilled_qty,
    ROUND(
        100 * SUM(fulfilled_quantity)
        / NULLIF(SUM(ordered_quantity), 0),
        2
    ) AS fulfillment_pct
FROM ORDER_LINE
WHERE plant_id = 'PL03'
  AND product_id IN ('PR202', 'PR203', 'PR204', 'PR206')
GROUP BY product_id
ORDER BY fulfillment_pct;

-- 3. Shipment performance by affected product
SELECT
    product_id,
    COUNT(*) AS shipment_count,
    SUM(shipped_quantity) AS shipped_qty,
    SUM(IFF(
        actual_delivery_date IS NOT NULL
        AND actual_delivery_date <= promised_date,
        1, 0
    )) AS on_time_shipments,
    ROUND(
        100.0 * SUM(IFF(
            actual_delivery_date IS NOT NULL
            AND actual_delivery_date <= promised_date,
            1, 0
        ))
        / NULLIF(SUM(IFF(actual_delivery_date IS NOT NULL, 1, 0)), 0),
        2
    ) AS on_time_delivery_pct
FROM SHIPMENT
WHERE plant_id = 'PL03'
  AND product_id IN ('PR202', 'PR203', 'PR204', 'PR206')
GROUP BY product_id
ORDER BY on_time_delivery_pct;
