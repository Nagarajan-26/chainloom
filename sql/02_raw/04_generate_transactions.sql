-- ChainLoom
-- Synthetic transaction generation
-- Version: 1.1
-- Purpose: Generate a deterministic, controlled operational scenario.
--
-- Scenario window: 2026-06-01 through 2026-08-31.
--
-- Deliberate disruption:
--   Supplier S017
--   Part P104
--   Plant PL03
--   Disruption begins 2026-08-01.
--
-- IMPORTANT:
-- RANDOM/UNIFORM are intentionally not used for the ground-truth scenario.
-- Snowflake documents that repeated RANDOM execution is not guaranteed to
-- reproduce the same row set. Deterministic formulas are used instead.

USE DATABASE CHAINLOOM;
USE SCHEMA RAW;

-- ------------------------------------------------------------
-- Purchase-order lines
-- ------------------------------------------------------------
INSERT INTO PURCHASE_ORDER_LINE
    (PO_LINE_ID, PO_ID, SUPPLIER_ID, PART_ID, PLANT_ID,
     ORDER_DATE, PROMISED_RECEIPT_DATE, ORDERED_QUANTITY, UNIT_COST, PO_LINE_STATUS)
SELECT
    'PO-' || LPAD(ROW_NUMBER() OVER (ORDER BY SP.SUPPLIER_PART_ID, D.CALENDAR_DATE), 6, '0'),
    'POH-' || LPAD(ROW_NUMBER() OVER (ORDER BY SP.SUPPLIER_PART_ID, D.CALENDAR_DATE), 6, '0'),
    SP.SUPPLIER_ID,
    SP.PART_ID,
    CASE MOD(ROW_NUMBER() OVER (ORDER BY SP.SUPPLIER_PART_ID, D.CALENDAR_DATE), 3)
        WHEN 0 THEN 'PL01'
        WHEN 1 THEN 'PL02'
        ELSE 'PL03'
    END,
    D.CALENDAR_DATE,
    DATEADD(day,
        CASE
            WHEN SP.SUPPLIER_ID = 'S017'
             AND SP.PART_ID = 'P104'
             AND D.CALENDAR_DATE >= '2026-08-01'::DATE
            THEN 12
            ELSE 5
        END,
        D.CALENDAR_DATE),
    80 + MOD(ROW_NUMBER() OVER (ORDER BY SP.SUPPLIER_PART_ID, D.CALENDAR_DATE) * 17, 121),
    P.STANDARD_COST,
    'Open'
FROM SUPPLIER_PART SP
JOIN PART P
  ON P.PART_ID = SP.PART_ID
JOIN DATE_DIM D
  ON D.CALENDAR_DATE BETWEEN '2026-06-05'::DATE AND '2026-08-20'::DATE
WHERE MOD(D.DATE_KEY + LENGTH(SP.PART_ID), 9) = 0
QUALIFY ROW_NUMBER() OVER (ORDER BY SP.SUPPLIER_PART_ID, D.CALENDAR_DATE) <= 220;

-- Force a visible set of disruption purchase commitments at PL03.
INSERT INTO PURCHASE_ORDER_LINE
    (PO_LINE_ID, PO_ID, SUPPLIER_ID, PART_ID, PLANT_ID,
     ORDER_DATE, PROMISED_RECEIPT_DATE, ORDERED_QUANTITY, UNIT_COST, PO_LINE_STATUS)
VALUES
    ('PO-900001','POH-900001','S017','P104','PL03','2026-07-24','2026-07-30',180,72.00,'Partially Received'),
    ('PO-900002','POH-900002','S017','P104','PL03','2026-07-29','2026-08-04',220,72.00,'Open'),
    ('PO-900003','POH-900003','S017','P104','PL03','2026-08-03','2026-08-10',240,72.00,'Open'),
    ('PO-900004','POH-900004','S017','P104','PL03','2026-08-10','2026-08-17',260,72.00,'Open');

-- ------------------------------------------------------------
-- Supply receipts
-- ------------------------------------------------------------
INSERT INTO SUPPLY_RECEIPT
    (RECEIPT_ID, PO_LINE_ID, SUPPLIER_ID, PART_ID, PLANT_ID,
     RECEIPT_DATE, RECEIVED_QUANTITY, ACCEPTED_QUANTITY, REJECTED_QUANTITY, RECEIPT_STATUS)
SELECT
    'RC-' || LPAD(ROW_NUMBER() OVER (ORDER BY PO.PO_LINE_ID), 6, '0'),
    PO.PO_LINE_ID,
    PO.SUPPLIER_ID,
    PO.PART_ID,
    PO.PLANT_ID,
    CASE
        WHEN PO.PO_LINE_ID = 'PO-900001' THEN '2026-08-08'::DATE
        WHEN PO.SUPPLIER_ID = 'S017'
         AND PO.PART_ID = 'P104'
         AND PO.ORDER_DATE >= '2026-08-01'::DATE
            THEN DATEADD(day, 10, PO.PROMISED_RECEIPT_DATE)
        ELSE PO.PROMISED_RECEIPT_DATE
    END,
    CASE
        WHEN PO.PO_LINE_ID = 'PO-900001' THEN 90
        WHEN PO.SUPPLIER_ID = 'S017'
         AND PO.PART_ID = 'P104'
         AND PO.ORDER_DATE >= '2026-08-01'::DATE
            THEN 0
        ELSE PO.ORDERED_QUANTITY
    END,
    CASE
        WHEN PO.PO_LINE_ID = 'PO-900001' THEN 90
        WHEN PO.SUPPLIER_ID = 'S017'
         AND PO.PART_ID = 'P104'
         AND PO.ORDER_DATE >= '2026-08-01'::DATE
            THEN 0
        ELSE PO.ORDERED_QUANTITY
    END,
    CASE
        WHEN PO.PO_LINE_ID = 'PO-900001' THEN 0
        ELSE 0
    END,
    CASE
        WHEN PO.PO_LINE_ID = 'PO-900001' THEN 'Partial'
        WHEN PO.SUPPLIER_ID = 'S017'
         AND PO.PART_ID = 'P104'
         AND PO.ORDER_DATE >= '2026-08-01'::DATE
            THEN 'Partial'
        ELSE 'Accepted'
    END
FROM PURCHASE_ORDER_LINE PO
WHERE PO.PO_LINE_ID <> 'PO-900004';

-- ------------------------------------------------------------
-- Inventory snapshots
-- Deterministic formula, with an explicit P104 / PL03 decline.
-- ------------------------------------------------------------
INSERT INTO INVENTORY
    (INVENTORY_SNAPSHOT_ID, PART_ID, PLANT_ID, SNAPSHOT_DATE,
     ON_HAND_QUANTITY, RESERVED_QUANTITY, AVAILABLE_QUANTITY, SAFETY_STOCK_QUANTITY)
SELECT
    'INV-' || PART.PART_ID || '-' || PL.PLANT_ID || '-' || TO_CHAR(D.CALENDAR_DATE,'YYYYMMDD'),
    PART.PART_ID,
    PL.PLANT_ID,
    D.CALENDAR_DATE,
    CASE
        WHEN PART.PART_ID = 'P104' AND PL.PLANT_ID = 'PL03'
         AND D.CALENDAR_DATE >= '2026-08-01'::DATE
            THEN GREATEST(35, 210 - DATEDIFF(day, '2026-08-01'::DATE, D.CALENDAR_DATE) * 7)
        ELSE 180 + MOD(DATE_PART(dayofyear, D.CALENDAR_DATE) + LENGTH(PART.PART_ID) * 11, 120)
    END,
    CASE
        WHEN PART.PART_ID = 'P104' AND PL.PLANT_ID = 'PL03'
         AND D.CALENDAR_DATE >= '2026-08-01'::DATE
            THEN LEAST(25, 10 + MOD(DATE_PART(dayofyear, D.CALENDAR_DATE), 16))
        ELSE 10 + MOD(DATE_PART(dayofyear, D.CALENDAR_DATE), 25)
    END,
    CASE
        WHEN PART.PART_ID = 'P104' AND PL.PLANT_ID = 'PL03'
         AND D.CALENDAR_DATE >= '2026-08-01'::DATE
            THEN GREATEST(20, 190 - DATEDIFF(day, '2026-08-01'::DATE, D.CALENDAR_DATE) * 7)
        ELSE GREATEST(
            0,
            180 + MOD(DATE_PART(dayofyear, D.CALENDAR_DATE) + LENGTH(PART.PART_ID) * 11, 120)
            - (10 + MOD(DATE_PART(dayofyear, D.CALENDAR_DATE), 25))
        )
    END,
    CASE
        WHEN PART.PART_ID = 'P104' THEN 150
        ELSE 90
    END
FROM PART
CROSS JOIN PLANT PL
JOIN DATE_DIM D
  ON D.CALENDAR_DATE BETWEEN '2026-07-01'::DATE AND '2026-08-31'::DATE;

-- ------------------------------------------------------------
-- Production
-- ------------------------------------------------------------
INSERT INTO PRODUCTION
    (PRODUCTION_ID, PLANT_ID, PRODUCT_ID, PRODUCTION_DATE,
     PLANNED_QUANTITY, PRODUCED_QUANTITY, DOWNTIME_HOURS, PRODUCTION_STATUS)
SELECT
    'PRD-' || PL.PLANT_ID || '-' || PROD.PRODUCT_ID || '-' || TO_CHAR(D.CALENDAR_DATE,'YYYYMMDD'),
    PL.PLANT_ID,
    PROD.PRODUCT_ID,
    D.CALENDAR_DATE,
    180 + MOD(DATE_PART(dayofyear, D.CALENDAR_DATE) + LENGTH(PROD.PRODUCT_ID), 70),
    CASE
        WHEN PL.PLANT_ID = 'PL03'
         AND PROD.PRODUCT_ID IN ('PR202','PR203','PR204','PR206')
         AND D.CALENDAR_DATE >= '2026-08-05'::DATE
            THEN GREATEST(
                60,
                180 + MOD(DATE_PART(dayofyear, D.CALENDAR_DATE) + LENGTH(PROD.PRODUCT_ID), 70) - 75
            )
        ELSE 180 + MOD(DATE_PART(dayofyear, D.CALENDAR_DATE) + LENGTH(PROD.PRODUCT_ID), 70)
    END,
    CASE
        WHEN PL.PLANT_ID = 'PL03'
         AND PROD.PRODUCT_ID IN ('PR202','PR203','PR204','PR206')
         AND D.CALENDAR_DATE >= '2026-08-05'::DATE
            THEN 6.0
        ELSE 1.0 + MOD(DATE_PART(dayofyear, D.CALENDAR_DATE), 4)
    END,
    CASE
        WHEN PL.PLANT_ID = 'PL03'
         AND PROD.PRODUCT_ID IN ('PR202','PR203','PR204','PR206')
         AND D.CALENDAR_DATE >= '2026-08-05'::DATE
            THEN 'Constrained'
        ELSE 'Normal'
    END
FROM PLANT PL
CROSS JOIN PRODUCT PROD
JOIN DATE_DIM D
  ON D.CALENDAR_DATE BETWEEN '2026-07-01'::DATE AND '2026-08-31'::DATE;

-- ------------------------------------------------------------
-- Quality
-- ------------------------------------------------------------
INSERT INTO QUALITY
    (INSPECTION_ID, SUPPLIER_ID, PART_ID, PLANT_ID, INSPECTION_DATE,
     INSPECTED_QUANTITY, DEFECTIVE_QUANTITY, DEFECT_TYPE, INSPECTION_STATUS)
SELECT
    'QI-' || LPAD(ROW_NUMBER() OVER (ORDER BY SP.SUPPLIER_PART_ID, D.CALENDAR_DATE), 6, '0'),
    SP.SUPPLIER_ID,
    SP.PART_ID,
    CASE MOD(D.DATE_KEY, 3)
        WHEN 0 THEN 'PL01'
        WHEN 1 THEN 'PL02'
        ELSE 'PL03'
    END,
    D.CALENDAR_DATE,
    100,
    CASE
        WHEN SP.SUPPLIER_ID = 'S017' AND SP.PART_ID = 'P104'
         AND D.CALENDAR_DATE >= '2026-08-01'::DATE
            THEN 12
        ELSE 2
    END,
    CASE
        WHEN SP.SUPPLIER_ID = 'S017' AND SP.PART_ID = 'P104'
         AND D.CALENDAR_DATE >= '2026-08-01'::DATE
            THEN 'Bearing surface defect'
        ELSE 'Normal variation'
    END,
    CASE
        WHEN SP.SUPPLIER_ID = 'S017' AND SP.PART_ID = 'P104'
         AND D.CALENDAR_DATE >= '2026-08-01'::DATE
            THEN 'Failed'
        ELSE 'Passed'
    END
FROM SUPPLIER_PART SP
JOIN DATE_DIM D
  ON D.CALENDAR_DATE BETWEEN '2026-07-01'::DATE AND '2026-08-31'::DATE
WHERE MOD(D.DATE_KEY + LENGTH(SP.PART_ID), 17) = 0;

-- ------------------------------------------------------------
-- Customer order lines
-- ------------------------------------------------------------
INSERT INTO ORDER_LINE
    (ORDER_LINE_ID, ORDER_ID, CUSTOMER_ID, PRODUCT_ID, PLANT_ID,
     ORDER_DATE, PROMISED_DATE, ORDERED_QUANTITY, FULFILLED_QUANTITY, ORDER_STATUS)
WITH N AS (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS N
    FROM TABLE(GENERATOR(ROWCOUNT => 240))
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
        WHEN MOD(N - 1, 11) = 0 THEN 0
        WHEN MOD(N - 1, 7) = 0 THEN LEAST(ORDERED_QUANTITY, 50 + MOD(N - 1, 30))
        ELSE ORDERED_QUANTITY
    END,
    CASE
        WHEN MOD(N - 1, 11) = 0 THEN 'Open'
        WHEN MOD(N - 1, 7) = 0 THEN 'Partially Fulfilled'
        ELSE 'Fulfilled'
    END
FROM B;

-- Explicit at-risk order cohort tied to P104-dependent products at PL03.
INSERT INTO ORDER_LINE
    (ORDER_LINE_ID, ORDER_ID, CUSTOMER_ID, PRODUCT_ID, PLANT_ID,
     ORDER_DATE, PROMISED_DATE, ORDERED_QUANTITY, FULFILLED_QUANTITY, ORDER_STATUS)
VALUES
    ('OL-900001','ORD-900001','C003','PR202','PL03','2026-08-04','2026-08-12',120,0,'Open'),
    ('OL-900002','ORD-900002','C007','PR203','PL03','2026-08-05','2026-08-13',90,0,'Open'),
    ('OL-900003','ORD-900003','C011','PR204','PL03','2026-08-06','2026-08-14',75,20,'Partially Fulfilled'),
    ('OL-900004','ORD-900004','C015','PR206','PL03','2026-08-07','2026-08-15',110,0,'Open'),
    ('OL-900005','ORD-900005','C019','PR202','PL03','2026-08-08','2026-08-16',80,0,'Open');

-- ------------------------------------------------------------
-- Shipments
-- ------------------------------------------------------------
INSERT INTO SHIPMENT
    (SHIPMENT_ID, ORDER_LINE_ID, CUSTOMER_ID, PRODUCT_ID, PLANT_ID, CARRIER_ID,
     SHIP_DATE, PROMISED_DATE, ACTUAL_DELIVERY_DATE, SHIPPED_QUANTITY,
     SHIPMENT_STATUS, DELAY_REASON)
SELECT
    'SHP-' || OL.ORDER_LINE_ID,
    OL.ORDER_LINE_ID,
    OL.CUSTOMER_ID,
    OL.PRODUCT_ID,
    OL.PLANT_ID,
    CASE MOD(ABS(HASH(OL.ORDER_LINE_ID)), 4)
        WHEN 0 THEN 'CA01'
        WHEN 1 THEN 'CA02'
        WHEN 2 THEN 'CA03'
        ELSE 'CA04'
    END,
    DATEADD(day, 5, OL.ORDER_DATE),
    OL.PROMISED_DATE,
    CASE
        WHEN OL.ORDER_LINE_ID IN ('OL-900001','OL-900002','OL-900003','OL-900004','OL-900005')
            THEN DATEADD(day, 7, OL.PROMISED_DATE)
        WHEN MOD(ABS(HASH(OL.ORDER_LINE_ID)), 9) = 0
            THEN DATEADD(day, 2, OL.PROMISED_DATE)
        ELSE OL.PROMISED_DATE
    END,
    OL.FULFILLED_QUANTITY,
    CASE
        WHEN OL.ORDER_LINE_ID IN ('OL-900001','OL-900002','OL-900003','OL-900004','OL-900005')
            THEN 'Delayed'
        WHEN MOD(ABS(HASH(OL.ORDER_LINE_ID)), 9) = 0
            THEN 'Delayed'
        ELSE 'Delivered'
    END,
    CASE
        WHEN OL.ORDER_LINE_ID IN ('OL-900001','OL-900002','OL-900003','OL-900004','OL-900005')
            THEN 'Material availability'
        WHEN MOD(ABS(HASH(OL.ORDER_LINE_ID)), 9) = 0
            THEN 'Operational delay'
        ELSE NULL
    END
FROM ORDER_LINE OL
WHERE OL.ORDER_STATUS <> 'Cancelled'
  AND OL.FULFILLED_QUANTITY > 0;

-- Explicit delayed shipment records for open/partially fulfilled impacted orders.
INSERT INTO SHIPMENT
    (SHIPMENT_ID, ORDER_LINE_ID, CUSTOMER_ID, PRODUCT_ID, PLANT_ID, CARRIER_ID,
     SHIP_DATE, PROMISED_DATE, ACTUAL_DELIVERY_DATE, SHIPPED_QUANTITY,
     SHIPMENT_STATUS, DELAY_REASON)
SELECT
    'SHP-' || OL.ORDER_LINE_ID || '-PENDING',
    OL.ORDER_LINE_ID,
    OL.CUSTOMER_ID,
    OL.PRODUCT_ID,
    OL.PLANT_ID,
    'CA03',
    DATEADD(day, 5, OL.ORDER_DATE),
    OL.PROMISED_DATE,
    NULL,
    OL.FULFILLED_QUANTITY,
    'In Transit',
    'Material availability'
FROM ORDER_LINE OL
WHERE OL.ORDER_LINE_ID IN ('OL-900001','OL-900002','OL-900003','OL-900004','OL-900005')
  AND OL.FULFILLED_QUANTITY = 0;

-- Summary counts.
SELECT 'PURCHASE_ORDER_LINE' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM PURCHASE_ORDER_LINE
UNION ALL SELECT 'SUPPLY_RECEIPT', COUNT(*) FROM SUPPLY_RECEIPT
UNION ALL SELECT 'INVENTORY', COUNT(*) FROM INVENTORY
UNION ALL SELECT 'PRODUCTION', COUNT(*) FROM PRODUCTION
UNION ALL SELECT 'QUALITY', COUNT(*) FROM QUALITY
UNION ALL SELECT 'ORDER_LINE', COUNT(*) FROM ORDER_LINE
UNION ALL SELECT 'SHIPMENT', COUNT(*) FROM SHIPMENT
ORDER BY TABLE_NAME;
