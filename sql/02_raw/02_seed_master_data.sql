-- ChainLoom
-- Synthetic master-data seed
-- Version: 1.1
-- Purpose: Small, controlled reference population for the hackathon scenario.
--
-- IMPORTANT:
-- This script intentionally uses explicit values for business entities.
-- Critical scenario identifiers are stable:
--   Supplier S017
--   Part P104
--   Plant PL03
-- No real customer, supplier, employee, or operational data is used.

USE DATABASE CHAINLOOM;
USE SCHEMA RAW;

-- Re-runnable for development. Do not use TRUNCATE/DELETE here because
-- this script is intended to establish the controlled master population.
INSERT INTO SUPPLIER
    (SUPPLIER_ID, SUPPLIER_CODE, SUPPLIER_NAME, SUPPLIER_REGION, SUPPLIER_TIER, SUPPLIER_STATUS)
VALUES
    ('S011','SUP-011','Northstar Components','North India','Standard','Active'),
    ('S012','SUP-012','Vertex Industrial','West India','Preferred','Active'),
    ('S013','SUP-013','BluePeak Materials','South India','Preferred','Active'),
    ('S014','SUP-014','Orion Precision','West India','Strategic','Active'),
    ('S015','SUP-015','Delta Motion Works','East India','Standard','Active'),
    ('S016','SUP-016','Summit Electronics','South India','Strategic','Active'),
    ('S017','SUP-017','Apex Components','South India','Strategic','Active'),
    ('S018','SUP-018','Harbor Industrial Supply','North India','Standard','Active');

INSERT INTO PART
    (PART_ID, PART_CODE, PART_NAME, PART_CATEGORY, UNIT_OF_MEASURE, CRITICALITY, STANDARD_COST)
VALUES
    ('P101','PART-101','Control Module','Electronics','EA','High',185.00),
    ('P102','PART-102','Power Converter','Electronics','EA','High',140.00),
    ('P103','PART-103','Drive Housing','Mechanical','EA','Medium',95.00),
    ('P104','PART-104','Precision Bearing','Mechanical','EA','Critical',72.00),
    ('P105','PART-105','Thermal Sensor','Electronics','EA','High',38.00),
    ('P106','PART-106','Valve Assembly','Fluid','EA','High',61.00),
    ('P107','PART-107','Motor Coupling','Mechanical','EA','Medium',44.00),
    ('P108','PART-108','Signal Harness','Electronics','EA','Medium',26.00),
    ('P109','PART-109','Fastener Kit','Mechanical','EA','Low',8.00),
    ('P110','PART-110','Cooling Fan','Mechanical','EA','Medium',31.00);

INSERT INTO PRODUCT
    (PRODUCT_ID, PRODUCT_CODE, PRODUCT_NAME, PRODUCT_FAMILY, PRODUCT_CATEGORY, UNIT_PRICE)
VALUES
    ('PR201','PROD-201','Industrial Controller','Controls','Industrial Automation',950.00),
    ('PR202','PROD-202','Servo Drive','Motion','Industrial Automation',1250.00),
    ('PR203','PROD-203','Smart Pump','Fluid Systems','Industrial Equipment',1800.00),
    ('PR204','PROD-204','Precision Actuator','Motion','Industrial Equipment',1550.00),
    ('PR205','PROD-205','Thermal Control Unit','Controls','Industrial Equipment',1100.00),
    ('PR206','PROD-206','Compact Drive','Motion','Industrial Automation',875.00);

INSERT INTO PLANT
    (PLANT_ID, PLANT_CODE, PLANT_NAME, CITY, REGION, PLANT_TYPE, CAPACITY_UNITS_PER_DAY)
VALUES
    ('PL01','PLANT-01','Chennai Manufacturing','Chennai','South India','Manufacturing',520),
    ('PL02','PLANT-02','Pune Manufacturing','Pune','West India','Manufacturing',610),
    ('PL03','PLANT-03','Coimbatore Manufacturing','Coimbatore','South India','Manufacturing',470);

INSERT INTO CUSTOMER
    (CUSTOMER_ID, CUSTOMER_CODE, CUSTOMER_NAME, CUSTOMER_SEGMENT, CUSTOMER_REGION, CUSTOMER_PRIORITY)
SELECT
    'C' || LPAD(N, 3, '0'),
    'CUST-' || LPAD(N, 3, '0'),
    'Synthetic Customer ' || LPAD(N, 3, '0'),
    CASE MOD(N - 1, 3)
        WHEN 0 THEN 'Enterprise'
        WHEN 1 THEN 'Mid-Market'
        ELSE 'Standard'
    END,
    CASE MOD(N - 1, 4)
        WHEN 0 THEN 'South India'
        WHEN 1 THEN 'West India'
        WHEN 2 THEN 'North India'
        ELSE 'East India'
    END,
    CASE MOD(N - 1, 4)
        WHEN 0 THEN 'Strategic'
        WHEN 1 THEN 'High'
        ELSE 'Standard'
    END
FROM (
    SELECT ROW_NUMBER() OVER (ORDER BY SEQ4()) AS N
    FROM TABLE(GENERATOR(ROWCOUNT => 30))
);

INSERT INTO CARRIER
    (CARRIER_ID, CARRIER_CODE, CARRIER_NAME, SERVICE_LEVEL, CARRIER_REGION)
VALUES
    ('CA01','CAR-01','SwiftLine Logistics','Express','South India'),
    ('CA02','CAR-02','BlueRoute Freight','Standard','West India'),
    ('CA03','CAR-03','PrimeHaul Logistics','Priority','National'),
    ('CA04','CAR-04','MetroCargo','Standard','National');

-- Calendar: 2026-06-01 through 2026-08-31.
INSERT INTO DATE_DIM
    (DATE_KEY, CALENDAR_DATE, YEAR, QUARTER, MONTH, MONTH_NAME,
     WEEK_OF_YEAR, DAY_OF_WEEK, DAY_NAME, IS_WEEKEND)
WITH D AS (
    SELECT DATEADD(day, ROW_NUMBER() OVER (ORDER BY SEQ4()) - 1, '2026-06-01'::DATE) AS CALENDAR_DATE
    FROM TABLE(GENERATOR(ROWCOUNT => 92))
)
SELECT
    TO_NUMBER(TO_CHAR(CALENDAR_DATE, 'YYYYMMDD')),
    CALENDAR_DATE,
    YEAR(CALENDAR_DATE),
    QUARTER(CALENDAR_DATE),
    MONTH(CALENDAR_DATE),
    MONTHNAME(CALENDAR_DATE),
    WEEKOFYEAR(CALENDAR_DATE),
    DAYOFWEEKISO(CALENDAR_DATE),
    DAYNAME(CALENDAR_DATE),
    DAYOFWEEKISO(CALENDAR_DATE) IN (6,7)
FROM D;

-- Smoke checks.
SELECT 'SUPPLIER' AS TABLE_NAME, COUNT(*) AS ROW_COUNT FROM SUPPLIER
UNION ALL SELECT 'PART', COUNT(*) FROM PART
UNION ALL SELECT 'PRODUCT', COUNT(*) FROM PRODUCT
UNION ALL SELECT 'PLANT', COUNT(*) FROM PLANT
UNION ALL SELECT 'CUSTOMER', COUNT(*) FROM CUSTOMER
UNION ALL SELECT 'CARRIER', COUNT(*) FROM CARRIER
UNION ALL SELECT 'DATE_DIM', COUNT(*) FROM DATE_DIM
ORDER BY TABLE_NAME;
