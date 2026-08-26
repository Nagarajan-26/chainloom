-- ChainLoom
-- Ground-truth gate
-- Version: 1.3

USE DATABASE CHAINLOOM;
USE SCHEMA RAW;

-- Supplier signal
SELECT
    po.supplier_id,
    COUNT(*) AS receipt_count,
    ROUND(
        AVG(DATEDIFF('day', po.promised_receipt_date, r.receipt_date)),
        2
    ) AS avg_receipt_delay_days
FROM PURCHASE_ORDER_LINE po
JOIN SUPPLY_RECEIPT r
    ON po.po_line_id = r.po_line_id
GROUP BY po.supplier_id
ORDER BY avg_receipt_delay_days DESC;

-- P104 inventory pressure
SELECT
    MIN(snapshot_date) AS first_snapshot,
    MIN(IFF(
        available_quantity < safety_stock_quantity,
        snapshot_date,
        NULL
    )) AS first_below_safety_stock,
    MIN(available_quantity) AS minimum_available_quantity,
    MAX(safety_stock_quantity) AS safety_stock_quantity
FROM INVENTORY
WHERE part_id = 'P104'
  AND plant_id = 'PL03';

-- P104-dependent products
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

-- First constrained production date
SELECT
    product_id,
    MIN(production_date) AS first_constrained_date
FROM PRODUCTION
WHERE plant_id = 'PL03'
  AND production_status = 'Constrained'
  AND product_id IN ('PR202', 'PR203', 'PR204', 'PR206')
GROUP BY product_id
ORDER BY first_constrained_date, product_id;
