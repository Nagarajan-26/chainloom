-- ChainLoom Semantic View v2.1 validation
USE DATABASE CHAINLOOM;
USE SCHEMA SEMANTIC;

SHOW SEMANTIC VIEWS IN SCHEMA CHAINLOOM.SEMANTIC;

DESC SEMANTIC VIEW CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS;

SELECT *
FROM SEMANTIC_VIEW(
  CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS
  DIMENSIONS supplier.supplier_id, supplier.supplier_name
  METRICS supply_receipt.receipt_count,
          supply_receipt.received_quantity
);

SELECT *
FROM SEMANTIC_VIEW(
  CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS
  DIMENSIONS part.part_id, part.part_name,
             plant.plant_id, plant.plant_name,
             inventory.snapshot_date
  METRICS inventory.available_quantity,
          inventory.safety_stock_quantity
);

SELECT *
FROM SEMANTIC_VIEW(
  CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS
  DIMENSIONS product.product_id, product.product_name,
             plant.plant_id, plant.plant_name
  METRICS production.production_day_count,
          production.planned_quantity,
          production.produced_quantity
);

SELECT *
FROM SEMANTIC_VIEW(
  CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS
  DIMENSIONS product.product_id, product.product_name
  METRICS order_line.order_line_count,
          order_line.ordered_quantity,
          order_line.fulfilled_quantity
);

SELECT *
FROM SEMANTIC_VIEW(
  CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS
  DIMENSIONS product.product_id, product.product_name
  METRICS shipment.shipment_count,
          shipment.shipped_quantity
);
