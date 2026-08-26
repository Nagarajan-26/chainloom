-- ChainLoom
-- RAW layer DDL
-- Version: 1.1
-- Purpose: Source-like synthetic operational tables.
--
-- Design note:
-- These tables intentionally resemble source-system entities rather than
-- curated DIM_/FACT_ objects. Business-facing semantics are introduced later
-- in the CURATED and SEMANTIC layers.
--
-- Snowflake standard-table PK/FK constraints are informational rather than
-- enforced. We therefore validate referential integrity explicitly in the
-- validation layer.

USE DATABASE CHAINLOOM;
USE SCHEMA RAW;

-- ============================================================
-- 1. SUPPLIER
-- Grain: one row per supplier
-- ============================================================
CREATE TABLE IF NOT EXISTS SUPPLIER (
    SUPPLIER_ID VARCHAR(20) NOT NULL PRIMARY KEY COMMENT 'Stable supplier business identifier',
    SUPPLIER_CODE VARCHAR(30) NOT NULL COMMENT 'Source supplier code',
    SUPPLIER_NAME VARCHAR(200) NOT NULL COMMENT 'Supplier business name',
    SUPPLIER_REGION VARCHAR(100) COMMENT 'Supplier operating region',
    SUPPLIER_TIER VARCHAR(30) COMMENT 'Strategic, Preferred, Standard',
    SUPPLIER_STATUS VARCHAR(30) COMMENT 'Active, Inactive, Suspended'
)
COMMENT = 'RAW supplier master data; grain: one row per supplier';

-- ============================================================
-- 2. PART
-- Grain: one row per part
-- ============================================================
CREATE TABLE IF NOT EXISTS PART (
    PART_ID VARCHAR(20) NOT NULL PRIMARY KEY COMMENT 'Stable part business identifier',
    PART_CODE VARCHAR(30) NOT NULL COMMENT 'Source part code',
    PART_NAME VARCHAR(200) NOT NULL COMMENT 'Part description',
    PART_CATEGORY VARCHAR(100) COMMENT 'Business part category',
    UNIT_OF_MEASURE VARCHAR(20) COMMENT 'Inventory unit of measure',
    CRITICALITY VARCHAR(30) COMMENT 'Criticality classification',
    STANDARD_COST NUMBER(18,2) COMMENT 'Standard unit cost'
)
COMMENT = 'RAW part master data; grain: one row per part';

-- ============================================================
-- 3. PRODUCT
-- Grain: one row per product
-- ============================================================
CREATE TABLE IF NOT EXISTS PRODUCT (
    PRODUCT_ID VARCHAR(20) NOT NULL PRIMARY KEY COMMENT 'Stable product business identifier',
    PRODUCT_CODE VARCHAR(30) NOT NULL COMMENT 'Source product code',
    PRODUCT_NAME VARCHAR(200) NOT NULL COMMENT 'Product name',
    PRODUCT_FAMILY VARCHAR(100) COMMENT 'Product family',
    PRODUCT_CATEGORY VARCHAR(100) COMMENT 'Product category',
    UNIT_PRICE NUMBER(18,2) COMMENT 'Reference selling price per unit'
)
COMMENT = 'RAW product master data; grain: one row per product';

-- ============================================================
-- 4. PLANT
-- Grain: one row per plant
-- ============================================================
CREATE TABLE IF NOT EXISTS PLANT (
    PLANT_ID VARCHAR(20) NOT NULL PRIMARY KEY COMMENT 'Stable plant business identifier',
    PLANT_CODE VARCHAR(30) NOT NULL COMMENT 'Source plant code',
    PLANT_NAME VARCHAR(200) NOT NULL COMMENT 'Plant name',
    CITY VARCHAR(100) COMMENT 'Plant city',
    REGION VARCHAR(100) COMMENT 'Plant region',
    PLANT_TYPE VARCHAR(50) COMMENT 'Manufacturing or distribution classification',
    CAPACITY_UNITS_PER_DAY NUMBER(18,2) COMMENT 'Nominal daily production capacity'
)
COMMENT = 'RAW plant master data; grain: one row per plant';

-- ============================================================
-- 5. CUSTOMER
-- Grain: one row per customer
-- ============================================================
CREATE TABLE IF NOT EXISTS CUSTOMER (
    CUSTOMER_ID VARCHAR(20) NOT NULL PRIMARY KEY COMMENT 'Stable customer business identifier',
    CUSTOMER_CODE VARCHAR(30) NOT NULL COMMENT 'Source customer code',
    CUSTOMER_NAME VARCHAR(200) NOT NULL COMMENT 'Customer name',
    CUSTOMER_SEGMENT VARCHAR(100) COMMENT 'Customer segment',
    CUSTOMER_REGION VARCHAR(100) COMMENT 'Customer region',
    CUSTOMER_PRIORITY VARCHAR(30) COMMENT 'Strategic, High, Standard'
)
COMMENT = 'RAW customer master data; grain: one row per customer';

-- ============================================================
-- 6. CARRIER
-- Grain: one row per carrier
-- ============================================================
CREATE TABLE IF NOT EXISTS CARRIER (
    CARRIER_ID VARCHAR(20) NOT NULL PRIMARY KEY COMMENT 'Stable carrier business identifier',
    CARRIER_CODE VARCHAR(30) NOT NULL COMMENT 'Source carrier code',
    CARRIER_NAME VARCHAR(200) NOT NULL COMMENT 'Carrier name',
    SERVICE_LEVEL VARCHAR(50) COMMENT 'Service level',
    CARRIER_REGION VARCHAR(100) COMMENT 'Carrier operating region'
)
COMMENT = 'RAW carrier master data; grain: one row per carrier';

-- ============================================================
-- 7. DATE
-- Grain: one row per calendar date
-- ============================================================
CREATE TABLE IF NOT EXISTS DATE_DIM (
    DATE_KEY NUMBER(8,0) NOT NULL PRIMARY KEY COMMENT 'YYYYMMDD date key',
    CALENDAR_DATE DATE NOT NULL COMMENT 'Calendar date',
    YEAR NUMBER(4,0) NOT NULL COMMENT 'Calendar year',
    QUARTER NUMBER(1,0) NOT NULL COMMENT 'Calendar quarter',
    MONTH NUMBER(2,0) NOT NULL COMMENT 'Calendar month number',
    MONTH_NAME VARCHAR(20) NOT NULL COMMENT 'Calendar month name',
    WEEK_OF_YEAR NUMBER(2,0) NOT NULL COMMENT 'ISO-style week number',
    DAY_OF_WEEK NUMBER(1,0) NOT NULL COMMENT 'Day of week number',
    DAY_NAME VARCHAR(20) NOT NULL COMMENT 'Day name',
    IS_WEEKEND BOOLEAN NOT NULL COMMENT 'Whether the date is Saturday or Sunday'
)
COMMENT = 'RAW calendar date data; grain: one row per calendar date';

-- ============================================================
-- 8. SUPPLIER_PART
-- Grain: one row per supplier-part sourcing relationship
-- ============================================================
CREATE TABLE IF NOT EXISTS SUPPLIER_PART (
    SUPPLIER_PART_ID VARCHAR(30) NOT NULL PRIMARY KEY COMMENT 'Stable supplier-part relationship identifier',
    SUPPLIER_ID VARCHAR(20) NOT NULL COMMENT 'Supplier identifier',
    PART_ID VARCHAR(20) NOT NULL COMMENT 'Part identifier',
    PREFERRED_SUPPLIER_FLAG BOOLEAN COMMENT 'Whether supplier is preferred for this part',
    ALLOCATION_PERCENT NUMBER(5,2) COMMENT 'Nominal allocation percentage',
    EFFECTIVE_START_DATE DATE COMMENT 'Relationship effective start',
    EFFECTIVE_END_DATE DATE COMMENT 'Relationship effective end'
)
COMMENT = 'RAW supplier-part sourcing relationships; grain: one row per supplier-part relationship';

-- ============================================================
-- 9. PRODUCT_PART
-- Grain: one row per product-part BOM relationship
-- ============================================================
CREATE TABLE IF NOT EXISTS PRODUCT_PART (
    PRODUCT_PART_ID VARCHAR(30) NOT NULL PRIMARY KEY COMMENT 'Stable product-part relationship identifier',
    PRODUCT_ID VARCHAR(20) NOT NULL COMMENT 'Product identifier',
    PART_ID VARCHAR(20) NOT NULL COMMENT 'Part identifier',
    QUANTITY_PER_PRODUCT NUMBER(18,4) NOT NULL COMMENT 'Part quantity required per product unit',
    CRITICAL_PART_FLAG BOOLEAN COMMENT 'Whether part is critical to the product',
    EFFECTIVE_START_DATE DATE COMMENT 'BOM relationship effective start',
    EFFECTIVE_END_DATE DATE COMMENT 'BOM relationship effective end'
)
COMMENT = 'RAW product BOM relationships; grain: one row per product-part relationship';

-- ============================================================
-- 10. PURCHASE_ORDER_LINE
-- Grain: one row per purchase-order line
-- ============================================================
CREATE TABLE IF NOT EXISTS PURCHASE_ORDER_LINE (
    PO_LINE_ID VARCHAR(30) NOT NULL PRIMARY KEY COMMENT 'Stable purchase-order line identifier',
    PO_ID VARCHAR(30) NOT NULL COMMENT 'Purchase-order header identifier',
    SUPPLIER_ID VARCHAR(20) NOT NULL COMMENT 'Supplier identifier',
    PART_ID VARCHAR(20) NOT NULL COMMENT 'Part identifier',
    PLANT_ID VARCHAR(20) NOT NULL COMMENT 'Receiving plant identifier',
    ORDER_DATE DATE NOT NULL COMMENT 'Purchase order creation date',
    PROMISED_RECEIPT_DATE DATE NOT NULL COMMENT 'Supplier promised receipt date',
    ORDERED_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Quantity ordered',
    UNIT_COST NUMBER(18,2) COMMENT 'Agreed unit cost',
    PO_LINE_STATUS VARCHAR(30) NOT NULL COMMENT 'Open, Partially Received, Received, Cancelled'
)
COMMENT = 'RAW purchase-order lines; grain: one row per PO line';

-- ============================================================
-- 11. SUPPLY_RECEIPT
-- Grain: one row per receipt event / receipt line
-- ============================================================
CREATE TABLE IF NOT EXISTS SUPPLY_RECEIPT (
    RECEIPT_ID VARCHAR(30) NOT NULL PRIMARY KEY COMMENT 'Stable receipt event identifier',
    PO_LINE_ID VARCHAR(30) NOT NULL COMMENT 'Purchase-order line identifier',
    SUPPLIER_ID VARCHAR(20) NOT NULL COMMENT 'Supplier identifier',
    PART_ID VARCHAR(20) NOT NULL COMMENT 'Part identifier',
    PLANT_ID VARCHAR(20) NOT NULL COMMENT 'Receiving plant identifier',
    RECEIPT_DATE DATE NOT NULL COMMENT 'Actual receipt date',
    RECEIVED_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Quantity physically received',
    ACCEPTED_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Quantity accepted after inspection',
    REJECTED_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Quantity rejected',
    RECEIPT_STATUS VARCHAR(30) NOT NULL COMMENT 'Accepted, Partial, Rejected'
)
COMMENT = 'RAW inbound supply receipts; grain: one row per receipt event / receipt line';

-- ============================================================
-- 12. INVENTORY
-- Grain: one row per part-plant-snapshot date
-- ============================================================
CREATE TABLE IF NOT EXISTS INVENTORY (
    INVENTORY_SNAPSHOT_ID VARCHAR(40) NOT NULL PRIMARY KEY COMMENT 'Stable inventory snapshot identifier',
    PART_ID VARCHAR(20) NOT NULL COMMENT 'Part identifier',
    PLANT_ID VARCHAR(20) NOT NULL COMMENT 'Plant identifier',
    SNAPSHOT_DATE DATE NOT NULL COMMENT 'Inventory snapshot date',
    ON_HAND_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Physical on-hand quantity',
    RESERVED_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Quantity reserved for demand',
    AVAILABLE_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'On-hand quantity available for use',
    SAFETY_STOCK_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Target safety stock quantity'
)
COMMENT = 'RAW inventory snapshots; grain: one row per part-plant-snapshot date';

-- ============================================================
-- 13. PRODUCTION
-- Grain: one row per plant-product-production date
-- ============================================================
CREATE TABLE IF NOT EXISTS PRODUCTION (
    PRODUCTION_ID VARCHAR(30) NOT NULL PRIMARY KEY COMMENT 'Stable production record identifier',
    PLANT_ID VARCHAR(20) NOT NULL COMMENT 'Plant identifier',
    PRODUCT_ID VARCHAR(20) NOT NULL COMMENT 'Product identifier',
    PRODUCTION_DATE DATE NOT NULL COMMENT 'Production date',
    PLANNED_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Planned production quantity',
    PRODUCED_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Actual production quantity',
    DOWNTIME_HOURS NUMBER(10,2) NOT NULL COMMENT 'Production downtime hours',
    PRODUCTION_STATUS VARCHAR(30) NOT NULL COMMENT 'Normal, Constrained, Delayed'
)
COMMENT = 'RAW production output; grain: one row per plant-product-production date';

-- ============================================================
-- 14. QUALITY
-- Grain: one row per supplier-part-plant inspection event
-- ============================================================
CREATE TABLE IF NOT EXISTS QUALITY (
    INSPECTION_ID VARCHAR(30) NOT NULL PRIMARY KEY COMMENT 'Stable quality inspection identifier',
    SUPPLIER_ID VARCHAR(20) NOT NULL COMMENT 'Supplier identifier',
    PART_ID VARCHAR(20) NOT NULL COMMENT 'Part identifier',
    PLANT_ID VARCHAR(20) NOT NULL COMMENT 'Plant identifier',
    INSPECTION_DATE DATE NOT NULL COMMENT 'Inspection date',
    INSPECTED_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Quantity inspected',
    DEFECTIVE_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Quantity classified defective',
    DEFECT_TYPE VARCHAR(100) COMMENT 'Defect category',
    INSPECTION_STATUS VARCHAR(30) NOT NULL COMMENT 'Passed, Failed, Conditional'
)
COMMENT = 'RAW quality inspection events; grain: one row per supplier-part-plant inspection event';

-- ============================================================
-- 15. ORDER_LINE
-- Grain: one row per customer order line
-- ============================================================
CREATE TABLE IF NOT EXISTS ORDER_LINE (
    ORDER_LINE_ID VARCHAR(30) NOT NULL PRIMARY KEY COMMENT 'Stable customer order line identifier',
    ORDER_ID VARCHAR(30) NOT NULL COMMENT 'Customer order header identifier',
    CUSTOMER_ID VARCHAR(20) NOT NULL COMMENT 'Customer identifier',
    PRODUCT_ID VARCHAR(20) NOT NULL COMMENT 'Product identifier',
    PLANT_ID VARCHAR(20) NOT NULL COMMENT 'Fulfillment plant identifier',
    ORDER_DATE DATE NOT NULL COMMENT 'Customer order date',
    PROMISED_DATE DATE NOT NULL COMMENT 'Promised customer delivery date',
    ORDERED_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Customer ordered quantity',
    FULFILLED_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Quantity fulfilled',
    ORDER_STATUS VARCHAR(30) NOT NULL COMMENT 'Open, Partially Fulfilled, Fulfilled, Cancelled'
)
COMMENT = 'RAW customer order lines; grain: one row per customer order line';

-- ============================================================
-- 16. SHIPMENT
-- Grain: one row per shipment event
-- ============================================================
CREATE TABLE IF NOT EXISTS SHIPMENT (
    SHIPMENT_ID VARCHAR(30) NOT NULL PRIMARY KEY COMMENT 'Stable shipment identifier',
    ORDER_LINE_ID VARCHAR(30) NOT NULL COMMENT 'Customer order line identifier',
    CUSTOMER_ID VARCHAR(20) NOT NULL COMMENT 'Customer identifier',
    PRODUCT_ID VARCHAR(20) NOT NULL COMMENT 'Product identifier',
    PLANT_ID VARCHAR(20) NOT NULL COMMENT 'Shipping plant identifier',
    CARRIER_ID VARCHAR(20) NOT NULL COMMENT 'Carrier identifier',
    SHIP_DATE DATE NOT NULL COMMENT 'Shipment dispatch date',
    PROMISED_DATE DATE NOT NULL COMMENT 'Promised customer delivery date',
    ACTUAL_DELIVERY_DATE DATE COMMENT 'Actual delivery date; null for undelivered shipments',
    SHIPPED_QUANTITY NUMBER(18,4) NOT NULL COMMENT 'Quantity shipped',
    SHIPMENT_STATUS VARCHAR(30) NOT NULL COMMENT 'In Transit, Delivered, Delayed, Cancelled',
    DELAY_REASON VARCHAR(200) COMMENT 'Operational delay reason when applicable'
)
COMMENT = 'RAW outbound shipments; grain: one row per shipment event';

-- ============================================================
-- Smoke-test inventory of the RAW layer
-- ============================================================
SHOW TABLES IN SCHEMA CHAINLOOM.RAW;
