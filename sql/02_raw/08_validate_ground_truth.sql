-- ChainLoom
-- Scenario ground-truth validation
-- Version: 1.2
--
-- Purpose: Verify that the intended investigation path is observable
-- without claiming deterministic causality.

USE DATABASE CHAINLOOM;
USE SCHEMA RAW;

-- A. Supplier signal
SELECT
    po.supplier_id,
    COUNT(*) AS receipt_count,
    ROUND(AVG(DATEDIFF('day', po.promised_receipt_date, r.receipt_date)), 2)
        AS avg_receipt_delay_days
FROM PURCHASE_ORDER_LINE po
JOIN SUPPLY_RECEIPT r
    ON po.po_line_id = r.po_line_id
GROUP BY po.supplier_id
ORDER BY avg_receipt_delay_days DESC;

-- B. P104 inventory pressure at PL03
SELECT
    MIN(snapshot_date) AS first_snapshot,
    MIN(IFF(available_quantity < safety_stock_quantity, snapshot_date, NULL))
        AS first_below_safety_stock,
    MIN(available_quantity) AS minimum_available_quantity,
    MAX(safety_stock_quantity) AS safety_stock_quantity
FROM INVENTORY
WHERE part_id = 'P104'
  AND plant_id = 'PL03';

-- C. P104-dependent products
SELECT
    pp.product_id,
    p.product_name,
    pp.quantity_per_product,
    pp.critical_part_flag
FROM PRODUCT_PART pp
JOIN PRODUCT p
    ON pp.product_id = p.product_id
WHERE pp.part_id = 'P104'
ORDER BY pp.product_id;

-- D. First constrained production date by affected product
SELECT
    product_id,
    MIN(production_date) AS first_constrained_date
FROM PRODUCTION
WHERE plant_id = 'PL03'
  AND production_status = 'Constrained'
  AND product_id IN ('PR202', 'PR203', 'PR204', 'PR206')
GROUP BY product_id
ORDER BY first_constrained_date, product_id;
