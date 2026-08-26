-- ChainLoom
-- RAW disruption refinement
-- Version: 1.2
-- Purpose: Replace overly synchronized synthetic downstream effects with
-- deterministic, product-specific severity while preserving the P104/PL03
-- supply-risk scenario.
--
-- IMPORTANT:
-- Run only after 01_create_raw_tables.sql through 05_validate_raw.sql.
-- This script intentionally rebuilds downstream synthetic facts from the
-- existing deterministic master/relationship data.

USE DATABASE CHAINLOOM;
USE SCHEMA RAW;

-- ============================================================
-- 1. Rebuild PRODUCTION with differentiated P104 exposure
-- ============================================================

TRUNCATE TABLE PRODUCTION;

INSERT INTO PRODUCTION
    (PRODUCTION_ID, PLANT_ID, PRODUCT_ID, PRODUCTION_DATE,
     PLANNED_QUANTITY, PRODUCED_QUANTITY, DOWNTIME_HOURS, PRODUCTION_STATUS)
WITH N AS (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS N
    FROM TABLE(GENERATOR(ROWCOUNT => 1116))
),
B AS (
    SELECT
        N,
        CASE MOD(N - 1, 3)
            WHEN 0 THEN 'PL01'
            WHEN 1 THEN 'PL02'
            ELSE 'PL03'
        END AS PLANT_ID,
        CASE MOD(FLOOR((N - 1) / 3), 6)
            WHEN 0 THEN 'PR201'
            WHEN 1 THEN 'PR202'
            WHEN 2 THEN 'PR203'
            WHEN 3 THEN 'PR204'
            WHEN 4 THEN 'PR205'
            ELSE 'PR206'
        END AS PRODUCT_ID,
        DATEADD(
            day,
            MOD(FLOOR((N - 1) / 18), 62),
            '2026-07-01'::DATE
        ) AS PRODUCTION_DATE
    FROM N
),
R AS (
    SELECT
        *,
        CASE PRODUCT_ID
            WHEN 'PR202' THEN 0.45
            WHEN 'PR204' THEN 0.35
            WHEN 'PR203' THEN 0.22
            WHEN 'PR206' THEN 0.15
            ELSE 0.00
        END AS DISRUPTION_RATE
    FROM B
),
Q AS (
    SELECT
        *,
        CASE PRODUCT_ID
            WHEN 'PR201' THEN 120
            WHEN 'PR202' THEN 150
            WHEN 'PR203' THEN 140
            WHEN 'PR204' THEN 150
            WHEN 'PR205' THEN 110
            ELSE 125
        END AS PLANNED_QTY
    FROM R
)
SELECT
    'PROD-' || LPAD(N, 6, '0'),
    PLANT_ID,
    PRODUCT_ID,
    PRODUCTION_DATE,
    PLANNED_QTY,
    CASE
        WHEN PLANT_ID = 'PL03'
         AND PRODUCTION_DATE >= '2026-08-05'::DATE
         AND DISRUPTION_RATE > 0
        THEN GREATEST(0, ROUND(PLANNED_QTY * (1 - DISRUPTION_RATE)))
        ELSE PLANNED_QTY
    END,
    CASE
        WHEN PLANT_ID = 'PL03'
         AND PRODUCTION_DATE >= '2026-08-05'::DATE
         AND DISRUPTION_RATE > 0
        THEN ROUND(2 + DISRUPTION_RATE * 12, 1)
        ELSE 1
    END,
    CASE
        WHEN PLANT_ID = 'PL03'
         AND PRODUCTION_DATE >= '2026-08-05'::DATE
         AND DISRUPTION_RATE > 0
        THEN 'Constrained'
        ELSE 'Normal'
    END
FROM Q;

-- ============================================================
-- 2. Rebuild ORDER_LINE with differentiated customer exposure
-- ============================================================

TRUNCATE TABLE ORDER_LINE;

INSERT INTO ORDER_LINE
    (ORDER_LINE_ID, ORDER_ID, CUSTOMER_ID, PRODUCT_ID, PLANT_ID,
     ORDER_DATE, PROMISED_DATE, ORDERED_QUANTITY, FULFILLED_QUANTITY, ORDER_STATUS)
WITH N AS (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS N
    FROM TABLE(GENERATOR(ROWCOUNT => 360))
),
B AS (
    SELECT
        N,
        'C' || LPAD(1 + MOD(N - 1, 30), 3, '0') AS CUSTOMER_ID,
        CASE MOD(N - 1, 6)
            WHEN 0 THEN 'PR201'
            WHEN 1 THEN 'PR202'
            WHEN 2 THEN 'PR203'
            WHEN 3 THEN 'PR204'
            WHEN 4 THEN 'PR205'
            ELSE 'PR206'
        END AS PRODUCT_ID,
        CASE MOD(N - 1, 3)
            WHEN 0 THEN 'PL01'
            WHEN 1 THEN 'PL02'
            ELSE 'PL03'
        END AS PLANT_ID,
        DATEADD(day, MOD(N - 1, 55), '2026-07-01'::DATE) AS ORDER_DATE,
        30 + MOD((N - 1) * 13, 91) AS ORDERED_QUANTITY
    FROM N
),
R AS (
    SELECT
        *,
        CASE PRODUCT_ID
            WHEN 'PR202' THEN 0.55
            WHEN 'PR204' THEN 0.65
            WHEN 'PR203' THEN 0.20
            WHEN 'PR206' THEN 0.12
            ELSE 0.00
        END AS FULFILLMENT_GAP_RATE
    FROM B
)
SELECT
    'OL-' || LPAD(N, 6, '0'),
    'ORD-' || LPAD(N, 6, '0'),
    CUSTOMER_ID,
    PRODUCT_ID,
    PLANT_ID,
    ORDER_DATE,
    DATEADD(day, 10 + MOD(N - 1, 8), ORDER_DATE),
    ORDERED_QUANTITY,
    CASE
        WHEN PLANT_ID = 'PL03'
         AND ORDER_DATE >= '2026-08-05'::DATE
         AND FULFILLMENT_GAP_RATE > 0
        THEN GREATEST(0, ROUND(ORDERED_QUANTITY * (1 - FULFILLMENT_GAP_RATE)))
        ELSE ORDERED_QUANTITY
    END,
    CASE
        WHEN PLANT_ID = 'PL03'
         AND ORDER_DATE >= '2026-08-05'::DATE
         AND FULFILLMENT_GAP_RATE >= 0.50
        THEN 'Open'
        WHEN PLANT_ID = 'PL03'
         AND ORDER_DATE >= '2026-08-05'::DATE
         AND FULFILLMENT_GAP_RATE > 0
        THEN 'Partially Fulfilled'
        ELSE 'Fulfilled'
    END
FROM R;

-- ============================================================
-- 3. Rebuild SHIPMENT from fulfilled order quantities
-- ============================================================

TRUNCATE TABLE SHIPMENT;

INSERT INTO SHIPMENT
    (SHIPMENT_ID, ORDER_LINE_ID, CUSTOMER_ID, PRODUCT_ID, PLANT_ID,
     CARRIER_ID, SHIP_DATE, PROMISED_DATE, ACTUAL_DELIVERY_DATE,
     SHIPPED_QUANTITY, SHIPMENT_STATUS, DELAY_REASON)
SELECT
    'SHIP-' || LPAD(ROW_NUMBER() OVER (ORDER BY ol.order_line_id), 6, '0'),
    ol.order_line_id,
    ol.customer_id,
    ol.product_id,
    ol.plant_id,
    'CA' || LPAD(1 + MOD(ABS(HASH(ol.order_line_id)), 4), 2, '0'),
    DATEADD(day, 3, ol.order_date),
    ol.promised_date,
    CASE
        WHEN ol.fulfilled_quantity = 0 THEN NULL
        WHEN ol.plant_id = 'PL03'
         AND ol.order_date >= '2026-08-05'::DATE
         AND ol.product_id = 'PR202'
            THEN DATEADD(day, 5, ol.promised_date)
        WHEN ol.plant_id = 'PL03'
         AND ol.order_date >= '2026-08-05'::DATE
         AND ol.product_id = 'PR204'
            THEN DATEADD(day, 4, ol.promised_date)
        WHEN ol.plant_id = 'PL03'
         AND ol.order_date >= '2026-08-05'::DATE
         AND ol.product_id = 'PR203'
            THEN DATEADD(day, 2, ol.promised_date)
        WHEN ol.plant_id = 'PL03'
         AND ol.order_date >= '2026-08-05'::DATE
         AND ol.product_id = 'PR206'
            THEN DATEADD(day, 1, ol.promised_date)
        ELSE ol.promised_date
    END,
    ol.fulfilled_quantity,
    CASE
        WHEN ol.fulfilled_quantity = 0 THEN 'In Transit'
        WHEN ol.plant_id = 'PL03'
         AND ol.order_date >= '2026-08-05'::DATE
         AND ol.product_id IN ('PR202', 'PR204', 'PR203', 'PR206')
            THEN 'Delayed'
        ELSE 'Delivered'
    END,
    CASE
        WHEN ol.fulfilled_quantity = 0 THEN NULL
        WHEN ol.plant_id = 'PL03'
         AND ol.order_date >= '2026-08-05'::DATE
            THEN 'Supply constraint'
        ELSE NULL
    END
FROM ORDER_LINE ol
WHERE ol.fulfilled_quantity > 0
   OR ol.order_status = 'Open';

-- ============================================================
-- 4. Quick post-refinement row-count check
-- ============================================================

SELECT
    table_name,
    row_count
FROM CHAINLOOM.INFORMATION_SCHEMA.TABLES
WHERE table_schema = 'RAW'
  AND table_name IN ('PRODUCTION', 'ORDER_LINE', 'SHIPMENT')
ORDER BY table_name;
