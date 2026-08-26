-- ChainLoom
-- FINAL RAW refinement
-- Version: 1.3
-- Purpose: Ensure all P104-dependent products have meaningful PL03 customer
-- exposure and that shipment delay severity follows the intended hierarchy.
--
-- This script rebuilds only ORDER_LINE and SHIPMENT.
-- Master data, relationships, receipts, inventory and production remain unchanged.

USE DATABASE CHAINLOOM;
USE SCHEMA RAW;

-- ============================================================
-- 1. Rebuild ORDER_LINE with explicit PL03 affected-product coverage
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
        CASE
            -- Deliberately guarantee 4 affected products at PL03.
            WHEN N BETWEEN 1 AND 90  THEN 'PR202'
            WHEN N BETWEEN 91 AND 180 THEN 'PR204'
            WHEN N BETWEEN 181 AND 270 THEN 'PR203'
            ELSE 'PR206'
        END AS PRODUCT_ID,
        CASE
            WHEN N BETWEEN 1 AND 90  THEN 'PL03'
            WHEN N BETWEEN 91 AND 180 THEN 'PL03'
            WHEN N BETWEEN 181 AND 270 THEN 'PL03'
            ELSE
                CASE MOD(N - 271, 3)
                    WHEN 0 THEN 'PL01'
                    WHEN 1 THEN 'PL02'
                    ELSE 'PL03'
                END
        END AS PLANT_ID,
        DATEADD(day, MOD(N - 1, 62), '2026-07-01'::DATE) AS ORDER_DATE,
        50 + MOD((N - 1) * 17, 101) AS ORDERED_QUANTITY
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
        END AS GAP_RATE
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
         AND GAP_RATE > 0
        THEN GREATEST(0, ROUND(ORDERED_QUANTITY * (1 - GAP_RATE)))
        ELSE ORDERED_QUANTITY
    END,
    CASE
        WHEN PLANT_ID = 'PL03'
         AND ORDER_DATE >= '2026-08-05'::DATE
         AND GAP_RATE >= 0.50
        THEN 'Open'
        WHEN PLANT_ID = 'PL03'
         AND ORDER_DATE >= '2026-08-05'::DATE
         AND GAP_RATE > 0
        THEN 'Partially Fulfilled'
        ELSE 'Fulfilled'
    END
FROM R;

-- ============================================================
-- 2. Rebuild SHIPMENT with differentiated delay severity
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
         AND ol.product_id IN ('PR202', 'PR203', 'PR204', 'PR206')
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
-- 3. Sanity check: all four affected products are represented
-- ============================================================

SELECT
    product_id,
    COUNT(*) AS order_lines,
    SUM(ordered_quantity) AS ordered_qty,
    SUM(fulfilled_quantity) AS fulfilled_qty,
    SUM(ordered_quantity - fulfilled_quantity) AS unfulfilled_qty
FROM ORDER_LINE
WHERE plant_id = 'PL03'
  AND product_id IN ('PR202', 'PR203', 'PR204', 'PR206')
GROUP BY product_id
ORDER BY product_id;

SELECT
    product_id,
    COUNT(*) AS shipment_count,
    SUM(shipped_quantity) AS shipped_qty
FROM SHIPMENT
WHERE plant_id = 'PL03'
  AND product_id IN ('PR202', 'PR203', 'PR204', 'PR206')
GROUP BY product_id
ORDER BY product_id;
