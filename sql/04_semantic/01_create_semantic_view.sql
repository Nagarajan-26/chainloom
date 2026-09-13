create or replace semantic view CHAINLOOM_ANALYTICS
	tables (
		CUSTOMER_FULFILLMENT as CHAINLOOM.CURATED.V_CUSTOMER_FULFILLMENT primary key (ORDER_LINE_ID) with synonyms=('customer orders','order fulfillment','demand fulfillment','order lines','customer demand','fill rate') comment='Customer order fulfillment fact table. Grain: one row per customer order line. Tracks ordered versus fulfilled quantities at the order-line level. Use for demand analysis, fill-rate measurement, and fulfillment gap identification. ',
		SHIPMENT_PERFORMANCE as CHAINLOOM.CURATED.V_SHIPMENT_PERFORMANCE primary key (SHIPMENT_ID) with synonyms=('shipments','deliveries','delivery performance','logistics','on-time delivery','OTD') comment='Outbound shipment delivery performance fact table. Grain: one row per shipment event. Tracks shipment timing, on-time delivery, and delay analysis. ',
		PRODUCTION_PERFORMANCE as CHAINLOOM.CURATED.V_PRODUCTION_PERFORMANCE primary key (PRODUCTION_ID) with synonyms=('production','manufacturing','production output','factory performance','plant output') comment='Production output performance fact table. Grain: one row per plant + product + production date. Tracks planned vs actual production, downtime, constraints, and Part P104 BOM exposure. ',
		INVENTORY_POSITION as CHAINLOOM.CURATED.V_INVENTORY_POSITION primary key (INVENTORY_SNAPSHOT_ID) with synonyms=('inventory','stock levels','inventory snapshots','stock on hand','warehouse inventory') comment='Inventory position snapshot fact table. Grain: one row per part + plant + snapshot date. SEMI-ADDITIVE: sum across parts/plants for one date only. Do NOT sum across dates. ',
		SUPPLIER_PERFORMANCE as CHAINLOOM.CURATED.V_SUPPLIER_PERFORMANCE with synonyms=('supplier scorecard','supplier quality','vendor performance','supplier metrics','procurement performance') comment='Supplier performance scorecard. Grain: one row per supplier-part relationship. Pre-aggregated. Ratio columns are non-additive. ',
		PRODUCT_RISK_SIGNALS as CHAINLOOM.CURATED.V_PRODUCT_RISK_SIGNALS primary key (PRODUCT_ID) with synonyms=('product risk','risk signals','multi-surface risk','product risk summary','supply chain risk') comment='Product-level risk signal summary. Grain: one row per product. Each signal (fulfillment, delivery, production) is independently computed from its respective analytical surface. RISK_SIGNAL_COUNT counts how many surfaces show risk indicators (0-3). Co-occurrence is observational only and does NOT imply causality between fulfillment gaps, delivery delays, and production constraints. ',
		CHAINLOOM.RAW.DATE_DIM primary key (CALENDAR_DATE) with synonyms=('calendar','dates','time dimension') comment='Calendar date dimension for time roll-up.',
		CHAINLOOM.RAW.PLANT primary key (PLANT_ID) with synonyms=('plants','facilities','factories','warehouses') comment='Plant dimension with city, type, and capacity.',
		CHAINLOOM.RAW.PRODUCT primary key (PRODUCT_ID) with synonyms=('products','finished goods','items') comment='Product dimension with family, category, and price.',
		CHAINLOOM.RAW.PART primary key (PART_ID) with synonyms=('parts','components','materials','raw materials') comment='Part dimension with criticality and cost.',
		CHAINLOOM.RAW.CARRIER primary key (CARRIER_ID) with synonyms=('carriers','logistics providers','shipping companies','transporters') comment='Carrier dimension with service level and region.'
	)
	relationships (
		FULFILLMENT_TO_DATE as CUSTOMER_FULFILLMENT(ORDER_DATE) references DATE_DIM(CALENDAR_DATE),
		FULFILLMENT_TO_PLANT as CUSTOMER_FULFILLMENT(PLANT_ID) references PLANT(PLANT_ID),
		FULFILLMENT_TO_PRODUCT as CUSTOMER_FULFILLMENT(PRODUCT_ID) references PRODUCT(PRODUCT_ID),
		SHIPMENT_TO_CARRIER as SHIPMENT_PERFORMANCE(CARRIER_ID) references CARRIER(CARRIER_ID),
		SHIPMENT_TO_DATE as SHIPMENT_PERFORMANCE(SHIP_DATE) references DATE_DIM(CALENDAR_DATE),
		SHIPMENT_TO_PLANT as SHIPMENT_PERFORMANCE(PLANT_ID) references PLANT(PLANT_ID),
		SHIPMENT_TO_PRODUCT as SHIPMENT_PERFORMANCE(PRODUCT_ID) references PRODUCT(PRODUCT_ID),
		PRODUCTION_TO_DATE as PRODUCTION_PERFORMANCE(PRODUCTION_DATE) references DATE_DIM(CALENDAR_DATE),
		PRODUCTION_TO_PLANT as PRODUCTION_PERFORMANCE(PLANT_ID) references PLANT(PLANT_ID),
		PRODUCTION_TO_PRODUCT as PRODUCTION_PERFORMANCE(PRODUCT_ID) references PRODUCT(PRODUCT_ID),
		INVENTORY_TO_DATE as INVENTORY_POSITION(SNAPSHOT_DATE) references DATE_DIM(CALENDAR_DATE),
		INVENTORY_TO_PART as INVENTORY_POSITION(PART_ID) references PART(PART_ID),
		INVENTORY_TO_PLANT as INVENTORY_POSITION(PLANT_ID) references PLANT(PLANT_ID),
		SUPPLIER_TO_PART as SUPPLIER_PERFORMANCE(PART_ID) references PART(PART_ID)
	)
	facts (
		CUSTOMER_FULFILLMENT.ORDERED_QUANTITY as ORDERED_QUANTITY with synonyms=('qty ordered','demand quantity','order quantity') comment='Quantity ordered by the customer.',
		CUSTOMER_FULFILLMENT.FULFILLED_QUANTITY as FULFILLED_QUANTITY with synonyms=('qty fulfilled','filled quantity') comment='Quantity fulfilled against this order line.',
		CUSTOMER_FULFILLMENT.UNFULFILLED_QUANTITY as UNFULFILLED_QUANTITY with synonyms=('qty unfulfilled','backorder quantity','open quantity') comment='Quantity not yet fulfilled.',
		SHIPMENT_PERFORMANCE.SHIPPED_QUANTITY as SHIPPED_QUANTITY with synonyms=('qty shipped','shipment quantity') comment='Quantity dispatched.',
		SHIPMENT_PERFORMANCE.DELIVERY_DELAY_DAYS as DELIVERY_DELAY_DAYS with synonyms=('delay days','days late') comment='Days between promised and actual delivery.',
		PRODUCTION_PERFORMANCE.PLANNED_QUANTITY as PLANNED_QUANTITY with synonyms=('planned output','target quantity','production plan') comment='Planned production quantity.',
		PRODUCTION_PERFORMANCE.PRODUCED_QUANTITY as PRODUCED_QUANTITY with synonyms=('actual output','actual production','units produced') comment='Actual production quantity.',
		PRODUCTION_PERFORMANCE.PRODUCTION_GAP_QUANTITY as PRODUCTION_GAP_QUANTITY with synonyms=('production shortfall','gap quantity','missed production') comment='Shortfall between planned and actual.',
		PRODUCTION_PERFORMANCE.DOWNTIME_HOURS as DOWNTIME_HOURS with synonyms=('downtime','hours down','lost hours') comment='Hours of production downtime.',
		INVENTORY_POSITION.ON_HAND_QUANTITY as ON_HAND_QUANTITY with synonyms=('on hand','stock on hand','physical stock') comment='Physical on-hand quantity. Semi-additive.',
		INVENTORY_POSITION.RESERVED_QUANTITY as RESERVED_QUANTITY with synonyms=('reserved','allocated quantity') comment='Quantity reserved. Semi-additive.',
		INVENTORY_POSITION.AVAILABLE_QUANTITY as AVAILABLE_QUANTITY with synonyms=('available stock','free stock','unreserved inventory') comment='Available quantity. Semi-additive.',
		INVENTORY_POSITION.SAFETY_STOCK_QUANTITY as SAFETY_STOCK_QUANTITY with synonyms=('safety stock','buffer stock','minimum stock') comment='Target safety stock. Semi-additive.',
		INVENTORY_POSITION.SAFETY_STOCK_GAP as SAFETY_STOCK_GAP with synonyms=('stock gap','safety stock shortfall') comment='Gap below safety stock. Semi-additive.',
		SUPPLIER_PERFORMANCE.PO_LINE_COUNT as PO_LINE_COUNT with synonyms=('purchase order lines','PO count') comment='PO lines placed.',
		SUPPLIER_PERFORMANCE.ORDERED_QUANTITY as ORDERED_QUANTITY with synonyms=('qty ordered from supplier','procurement quantity') comment='Quantity ordered from supplier.',
		SUPPLIER_PERFORMANCE.RECEIPT_COUNT as RECEIPT_COUNT with synonyms=('receipts','delivery count') comment='Receipt events.',
		SUPPLIER_PERFORMANCE.RECEIVED_QUANTITY as RECEIVED_QUANTITY with synonyms=('qty received') comment='Quantity received.',
		SUPPLIER_PERFORMANCE.ACCEPTED_QUANTITY as ACCEPTED_QUANTITY with synonyms=('qty accepted','good quantity') comment='Quantity accepted.',
		SUPPLIER_PERFORMANCE.REJECTED_QUANTITY as REJECTED_QUANTITY with synonyms=('qty rejected','failed quantity') comment='Quantity rejected.',
		SUPPLIER_PERFORMANCE.INSPECTED_QUANTITY as INSPECTED_QUANTITY with synonyms=('qty inspected') comment='Quantity inspected.',
		SUPPLIER_PERFORMANCE.DEFECTIVE_QUANTITY as DEFECTIVE_QUANTITY with synonyms=('qty defective','defects') comment='Defective quantity.',
		PRODUCT_RISK_SIGNALS.FULFILLMENT_RATE as FULFILLMENT_RATE with synonyms=('fill rate','product fulfillment rate') comment='Product-level fulfillment rate. NULL if no order history.',
		PRODUCT_RISK_SIGNALS.ON_TIME_DELIVERY_RATE as ON_TIME_DELIVERY_RATE with synonyms=('OTD rate','product delivery rate') comment='Product-level OTD rate. NULL if no delivery history.',
		PRODUCT_RISK_SIGNALS.PRODUCTION_ATTAINMENT as PRODUCTION_ATTAINMENT with synonyms=('attainment','product attainment') comment='Product-level production attainment. NULL if no production history.',
		PRODUCT_RISK_SIGNALS.ORDER_LINES_WITH_GAPS as ORDER_LINES_WITH_GAPS comment='Count of order lines with unfulfilled quantity.',
		PRODUCT_RISK_SIGNALS.ELIGIBLE_SHIPMENTS as ELIGIBLE_SHIPMENTS comment='Count of delivered shipments eligible for OTD calculation.',
		PRODUCT_RISK_SIGNALS.CONSTRAINED_DAYS as CONSTRAINED_DAYS comment='Count of production-days flagged as constrained.',
		PRODUCT_RISK_SIGNALS.TOTAL_PRODUCTION_DAYS as TOTAL_PRODUCTION_DAYS comment='Total production-days for this product.'
	)
	dimensions (
		CUSTOMER_FULFILLMENT.ORDER_LINE_ID as ORDER_LINE_ID with synonyms=('order line','line id') comment='Unique customer order line identifier.',
		CUSTOMER_FULFILLMENT.ORDER_ID as ORDER_ID with synonyms=('order number','order header') comment='Customer order header identifier.',
		CUSTOMER_FULFILLMENT.ORDER_DATE as ORDER_DATE with synonyms=('date ordered','order placed date') comment='Date the customer placed the order.',
		CUSTOMER_FULFILLMENT.PROMISED_DATE as PROMISED_DATE with synonyms=('promise date','committed date') comment='Date promised to the customer for delivery.',
		CUSTOMER_FULFILLMENT.CUSTOMER_ID as CUSTOMER_ID comment='Customer business identifier.',
		CUSTOMER_FULFILLMENT.CUSTOMER_NAME as CUSTOMER_NAME with synonyms=('customer','account name') comment='Customer name.',
		CUSTOMER_FULFILLMENT.CUSTOMER_SEGMENT as CUSTOMER_SEGMENT with synonyms=('segment','market segment') comment='Customer market segment classification.',
		CUSTOMER_FULFILLMENT.CUSTOMER_REGION as CUSTOMER_REGION with synonyms=('customer geography','customer location') comment='Geographic region of the customer.',
		CUSTOMER_FULFILLMENT.CUSTOMER_PRIORITY as CUSTOMER_PRIORITY with synonyms=('priority','customer tier') comment='Customer priority tier.',
		CUSTOMER_FULFILLMENT.PRODUCT_ID as PRODUCT_ID comment='Product identifier for the ordered item.',
		CUSTOMER_FULFILLMENT.PRODUCT_NAME as PRODUCT_NAME with synonyms=('product','item name') comment='Product name.',
		CUSTOMER_FULFILLMENT.PRODUCT_FAMILY as PRODUCT_FAMILY comment='Product family grouping.',
		CUSTOMER_FULFILLMENT.PRODUCT_CATEGORY as PRODUCT_CATEGORY comment='Product category classification.',
		CUSTOMER_FULFILLMENT.PLANT_ID as PLANT_ID comment='Fulfillment plant identifier.',
		CUSTOMER_FULFILLMENT.PLANT_NAME as PLANT_NAME with synonyms=('fulfillment plant','shipping plant') comment='Name of the plant fulfilling the order.',
		CUSTOMER_FULFILLMENT.PLANT_REGION as PLANT_REGION comment='Geographic region of the fulfillment plant.',
		CUSTOMER_FULFILLMENT.ORDER_STATUS as ORDER_STATUS with synonyms=('status','fulfillment status') comment='Current order line status.',
		CUSTOMER_FULFILLMENT.FULFILLMENT_GAP_FLAG as FULFILLMENT_GAP_FLAG with synonyms=('has gap','unfulfilled flag','backorder flag') comment='TRUE when this order line has unfulfilled quantity.',
		SHIPMENT_PERFORMANCE.SHIPMENT_ID as SHIPMENT_ID with synonyms=('shipment','delivery id') comment='Unique shipment event identifier.',
		SHIPMENT_PERFORMANCE.ORDER_LINE_ID as ORDER_LINE_ID comment='Related customer order line identifier.',
		SHIPMENT_PERFORMANCE.CUSTOMER_ID as CUSTOMER_ID comment='Customer receiving the shipment.',
		SHIPMENT_PERFORMANCE.CUSTOMER_NAME as CUSTOMER_NAME with synonyms=('customer') comment='Customer name.',
		SHIPMENT_PERFORMANCE.CUSTOMER_SEGMENT as CUSTOMER_SEGMENT with synonyms=('segment') comment='Customer market segment.',
		SHIPMENT_PERFORMANCE.CUSTOMER_REGION as CUSTOMER_REGION comment='Geographic region of the customer.',
		SHIPMENT_PERFORMANCE.CUSTOMER_PRIORITY as CUSTOMER_PRIORITY comment='Customer priority tier.',
		SHIPMENT_PERFORMANCE.PRODUCT_ID as PRODUCT_ID comment='Product shipped.',
		SHIPMENT_PERFORMANCE.PRODUCT_NAME as PRODUCT_NAME with synonyms=('product') comment='Product name.',
		SHIPMENT_PERFORMANCE.PRODUCT_FAMILY as PRODUCT_FAMILY comment='Product family grouping.',
		SHIPMENT_PERFORMANCE.PLANT_ID as PLANT_ID comment='Shipping plant identifier.',
		SHIPMENT_PERFORMANCE.PLANT_NAME as PLANT_NAME with synonyms=('shipping plant','origin plant') comment='Name of the shipping plant.',
		SHIPMENT_PERFORMANCE.PLANT_REGION as PLANT_REGION comment='Geographic region of the shipping plant.',
		SHIPMENT_PERFORMANCE.CARRIER_ID as CARRIER_ID comment='Carrier used for the shipment.',
		SHIPMENT_PERFORMANCE.CARRIER_NAME as CARRIER_NAME with synonyms=('carrier','logistics provider') comment='Carrier name.',
		SHIPMENT_PERFORMANCE.SERVICE_LEVEL as SERVICE_LEVEL with synonyms=('shipping speed','delivery tier') comment='Carrier service level.',
		SHIPMENT_PERFORMANCE.SHIP_DATE as SHIP_DATE with synonyms=('dispatch date','shipped date') comment='Date the shipment was dispatched.',
		SHIPMENT_PERFORMANCE.PROMISED_DATE as PROMISED_DATE with synonyms=('promise date','expected delivery') comment='Promised delivery date.',
		SHIPMENT_PERFORMANCE.ACTUAL_DELIVERY_DATE as ACTUAL_DELIVERY_DATE with synonyms=('delivered date','arrival date') comment='Actual delivery date. NULL for undelivered.',
		SHIPMENT_PERFORMANCE.SHIPMENT_STATUS as SHIPMENT_STATUS with synonyms=('status','delivery status') comment='Current shipment status.',
		SHIPMENT_PERFORMANCE.DELAY_REASON as DELAY_REASON with synonyms=('reason for delay','delay cause') comment='Operational reason for delay.',
		SHIPMENT_PERFORMANCE.ON_TIME_FLAG as ON_TIME_FLAG with synonyms=('on time','delivered on time') comment='TRUE when delivered on or before promised date.',
		SHIPMENT_PERFORMANCE.DELIVERY_ELIGIBLE_FLAG as DELIVERY_ELIGIBLE_FLAG with synonyms=('eligible for OTD','delivered flag') comment='TRUE when shipment is delivered and eligible for OTD calculation.',
		PRODUCTION_PERFORMANCE.PRODUCTION_ID as PRODUCTION_ID comment='Unique production record identifier.',
		PRODUCTION_PERFORMANCE.PRODUCTION_DATE as PRODUCTION_DATE with synonyms=('manufacturing date','production day') comment='Date of production activity.',
		PRODUCTION_PERFORMANCE.PLANT_ID as PLANT_ID comment='Plant where production occurred.',
		PRODUCTION_PERFORMANCE.PLANT_NAME as PLANT_NAME with synonyms=('factory','plant') comment='Plant name.',
		PRODUCTION_PERFORMANCE.PLANT_REGION as PLANT_REGION comment='Geographic region of the production plant.',
		PRODUCTION_PERFORMANCE.PRODUCT_ID as PRODUCT_ID comment='Product being produced.',
		PRODUCTION_PERFORMANCE.PRODUCT_NAME as PRODUCT_NAME with synonyms=('product') comment='Product name.',
		PRODUCTION_PERFORMANCE.PRODUCT_FAMILY as PRODUCT_FAMILY comment='Product family grouping.',
		PRODUCTION_PERFORMANCE.PRODUCT_CATEGORY as PRODUCT_CATEGORY comment='Product category classification.',
		PRODUCTION_PERFORMANCE.PRODUCTION_STATUS as PRODUCTION_STATUS with synonyms=('status','manufacturing status') comment='Production status for this day.',
		PRODUCTION_PERFORMANCE.CONSTRAINT_FLAG as CONSTRAINT_FLAG with synonyms=('constrained','capacity constrained') comment='TRUE when production was constrained.',
		PRODUCTION_PERFORMANCE.CRITICAL_PART_COUNT as CRITICAL_PART_COUNT comment='Number of critical parts in BOM.',
		PRODUCTION_PERFORMANCE.CRITICAL_PARTS as CRITICAL_PARTS comment='List of critical part names in BOM.',
		PRODUCTION_PERFORMANCE.P104_EXPOSURE_FLAG as P104_EXPOSURE_FLAG with synonyms=('p104 dependency','p104 exposed','uses part p104') comment='TRUE when product BOM includes Part P104. BOM dependency only.',
		PRODUCTION_PERFORMANCE.P104_QTY_PER_PRODUCT as P104_QTY_PER_PRODUCT with synonyms=('p104 usage per unit') comment='Quantity of P104 required per product unit.',
		INVENTORY_POSITION.INVENTORY_SNAPSHOT_ID as INVENTORY_SNAPSHOT_ID comment='Unique snapshot record identifier.',
		INVENTORY_POSITION.SNAPSHOT_DATE as SNAPSHOT_DATE with synonyms=('inventory date','as-of date','stock date') comment='Date of inventory snapshot. Always include in queries.',
		INVENTORY_POSITION.PART_ID as PART_ID comment='Part being tracked.',
		INVENTORY_POSITION.PART_NAME as PART_NAME with synonyms=('part','component') comment='Part name.',
		INVENTORY_POSITION.PART_CATEGORY as PART_CATEGORY comment='Business category of the part.',
		INVENTORY_POSITION.CRITICALITY as CRITICALITY with synonyms=('part criticality','importance level') comment='Criticality classification.',
		INVENTORY_POSITION.PLANT_ID as PLANT_ID comment='Plant holding the inventory.',
		INVENTORY_POSITION.PLANT_NAME as PLANT_NAME with synonyms=('warehouse','location') comment='Plant name.',
		INVENTORY_POSITION.PLANT_REGION as PLANT_REGION comment='Geographic region of the plant.',
		INVENTORY_POSITION.BELOW_SAFETY_STOCK_FLAG as BELOW_SAFETY_STOCK_FLAG with synonyms=('below safety stock','stockout risk','understocked') comment='TRUE when below safety stock target.',
		INVENTORY_POSITION.INVENTORY_RISK_BAND as INVENTORY_RISK_BAND with synonyms=('risk level','inventory risk') comment='Risk classification band.',
		SUPPLIER_PERFORMANCE.SUPPLIER_ID as SUPPLIER_ID comment='Supplier identifier.',
		SUPPLIER_PERFORMANCE.SUPPLIER_NAME as SUPPLIER_NAME with synonyms=('supplier','vendor') comment='Supplier name.',
		SUPPLIER_PERFORMANCE.SUPPLIER_REGION as SUPPLIER_REGION with synonyms=('vendor region') comment='Supplier region.',
		SUPPLIER_PERFORMANCE.SUPPLIER_TIER as SUPPLIER_TIER with synonyms=('tier','supplier classification') comment='Supplier tier.',
		SUPPLIER_PERFORMANCE.SUPPLIER_STATUS as SUPPLIER_STATUS with synonyms=('status','vendor status') comment='Supplier status.',
		SUPPLIER_PERFORMANCE.PART_ID as PART_ID comment='Part supplied.',
		SUPPLIER_PERFORMANCE.PART_NAME as PART_NAME with synonyms=('part','component') comment='Part name.',
		SUPPLIER_PERFORMANCE.PART_CATEGORY as PART_CATEGORY comment='Part category.',
		SUPPLIER_PERFORMANCE.CRITICALITY as CRITICALITY with synonyms=('part criticality') comment='Part criticality.',
		SUPPLIER_PERFORMANCE.PREFERRED_SUPPLIER_FLAG as PREFERRED_SUPPLIER_FLAG with synonyms=('preferred','primary supplier') comment='TRUE if preferred source.',
		SUPPLIER_PERFORMANCE.ALLOCATION_PERCENT as ALLOCATION_PERCENT with synonyms=('allocation','share percentage') comment='Nominal allocation percentage.',
		SUPPLIER_PERFORMANCE.SUPPLY_RISK_BAND as SUPPLY_RISK_BAND with synonyms=('risk band','supply risk') comment='Supply risk classification.',
		SUPPLIER_PERFORMANCE.AVG_RECEIPT_DELAY_DAYS as AVG_RECEIPT_DELAY_DAYS with synonyms=('average delay','receipt delay') comment='Pre-aggregated average receipt delay. NON-ADDITIVE.',
		SUPPLIER_PERFORMANCE.ON_TIME_RECEIPT_PCT as ON_TIME_RECEIPT_PCT with synonyms=('on-time rate','receipt on-time percentage') comment='Pre-aggregated on-time receipt pct. NON-ADDITIVE.',
		SUPPLIER_PERFORMANCE.DEFECT_RATE_PCT as DEFECT_RATE_PCT with synonyms=('defect percentage','quality failure rate') comment='Pre-aggregated defect rate pct. NON-ADDITIVE.',
		PRODUCT_RISK_SIGNALS.PRODUCT_ID as PRODUCT_ID comment='Product identifier.',
		PRODUCT_RISK_SIGNALS.PRODUCT_NAME as PRODUCT_NAME with synonyms=('product') comment='Product name.',
		PRODUCT_RISK_SIGNALS.FULFILLMENT_RISK_FLAG as FULFILLMENT_RISK_FLAG with synonyms=('fulfillment risk','demand risk') comment='TRUE when product fulfillment rate is below 90%. Independent signal from customer_fulfillment surface. ',
		PRODUCT_RISK_SIGNALS.DELIVERY_RISK_FLAG as DELIVERY_RISK_FLAG with synonyms=('delivery risk','shipping risk','OTD risk') comment='TRUE when product on-time delivery rate is below 85%. Independent signal from shipment_performance surface. ',
		PRODUCT_RISK_SIGNALS.PRODUCTION_RISK_FLAG as PRODUCTION_RISK_FLAG with synonyms=('production risk','manufacturing risk') comment='TRUE when product production attainment is below 90%. Independent signal from production_performance surface. ',
		PRODUCT_RISK_SIGNALS.RISK_SIGNAL_COUNT as RISK_SIGNAL_COUNT with synonyms=('signal count','risk count','number of risk signals') comment='Count of independent risk surfaces showing indicators (0-3). Observational co-occurrence only. Does NOT imply that one signal caused another. ',
		DATE_DIM.DATE_KEY as DATE_KEY comment='YYYYMMDD date key.',
		DATE_DIM.CALENDAR_DATE as CALENDAR_DATE with synonyms=('date') comment='Calendar date.',
		DATE_DIM.YEAR as YEAR with synonyms=('calendar year') comment='Calendar year.',
		DATE_DIM.QUARTER as QUARTER with synonyms=('calendar quarter','qtr') comment='Calendar quarter.',
		DATE_DIM.MONTH as MONTH with synonyms=('month number') comment='Month number.',
		DATE_DIM.MONTH_NAME as MONTH_NAME with synonyms=('month label') comment='Month name.',
		DATE_DIM.WEEK_OF_YEAR as WEEK_OF_YEAR with synonyms=('week number','week') comment='ISO week number.',
		DATE_DIM.DAY_OF_WEEK as DAY_OF_WEEK comment='Day of week number.',
		DATE_DIM.DAY_NAME as DAY_NAME comment='Day name.',
		DATE_DIM.IS_WEEKEND as IS_WEEKEND with synonyms=('weekend flag','weekend') comment='TRUE if weekend.',
		PLANT.PLANT_ID as PLANT_ID comment='Plant identifier.',
		PLANT.PLANT_CODE as PLANT_CODE comment='Source plant code.',
		PLANT.PLANT_NAME as PLANT_NAME with synonyms=('facility name') comment='Plant name.',
		PLANT.CITY as CITY with synonyms=('plant city','location') comment='Plant city.',
		PLANT.REGION as REGION with synonyms=('plant region') comment='Plant region.',
		PLANT.PLANT_TYPE as PLANT_TYPE with synonyms=('facility type') comment='Manufacturing or Distribution.',
		PLANT.CAPACITY_UNITS_PER_DAY as CAPACITY_UNITS_PER_DAY with synonyms=('daily capacity','production capacity') comment='Daily production capacity.',
		PRODUCT.PRODUCT_ID as PRODUCT_ID comment='Product identifier.',
		PRODUCT.PRODUCT_CODE as PRODUCT_CODE comment='Source product code.',
		PRODUCT.PRODUCT_NAME as PRODUCT_NAME comment='Product name.',
		PRODUCT.PRODUCT_FAMILY as PRODUCT_FAMILY comment='Product family.',
		PRODUCT.PRODUCT_CATEGORY as PRODUCT_CATEGORY comment='Product category.',
		PRODUCT.UNIT_PRICE as UNIT_PRICE with synonyms=('price','list price','selling price') comment='Reference selling price.',
		PART.PART_ID as PART_ID comment='Part identifier.',
		PART.PART_CODE as PART_CODE comment='Source part code.',
		PART.PART_NAME as PART_NAME with synonyms=('component name') comment='Part name.',
		PART.PART_CATEGORY as PART_CATEGORY comment='Part category.',
		PART.UNIT_OF_MEASURE as UNIT_OF_MEASURE with synonyms=('UoM','unit') comment='Unit of measure.',
		PART.CRITICALITY as CRITICALITY with synonyms=('importance','critical level') comment='Criticality classification.',
		PART.STANDARD_COST as STANDARD_COST with synonyms=('unit cost','cost per unit') comment='Standard unit cost.',
		CARRIER.CARRIER_ID as CARRIER_ID comment='Carrier identifier.',
		CARRIER.CARRIER_CODE as CARRIER_CODE comment='Source carrier code.',
		CARRIER.CARRIER_NAME as CARRIER_NAME with synonyms=('carrier','transporter name') comment='Carrier name.',
		CARRIER.SERVICE_LEVEL as SERVICE_LEVEL with synonyms=('shipping speed','delivery tier') comment='Service level.',
		CARRIER.CARRIER_REGION as CARRIER_REGION with synonyms=('operating region','coverage area') comment='Operating region.'
	)
	metrics (
		CUSTOMER_FULFILLMENT.FULFILLMENT_RATE as SUM(FULFILLED_QUANTITY) / NULLIF(SUM(ORDERED_QUANTITY), 0) with synonyms=('fill rate','order fill rate','fulfillment percentage','service level') comment='Ratio of fulfilled to ordered quantity.',
		CUSTOMER_FULFILLMENT.ORDER_LINES_WITH_FULFILLMENT_GAPS as COUNT_IF(FULFILLMENT_GAP_FLAG = TRUE) with synonyms=('gap count','unfulfilled order lines','backorder count') comment='Count of order lines with unfulfilled quantity.',
		SHIPMENT_PERFORMANCE.ON_TIME_DELIVERY_RATE as COUNT_IF(ON_TIME_FLAG = TRUE) / NULLIF(COUNT_IF(DELIVERY_ELIGIBLE_FLAG = TRUE), 0) with synonyms=('OTD rate','on-time percentage','delivery reliability','OTIF rate') comment='Ratio of on-time to eligible delivered shipments.',
		SHIPMENT_PERFORMANCE.AVG_DELIVERY_DELAY_DAYS as AVG(CASE WHEN DELIVERY_ELIGIBLE_FLAG = TRUE THEN DELIVERY_DELAY_DAYS END) with synonyms=('average delay','mean delay days','average lateness') comment='Average delay for eligible delivered shipments.',
		PRODUCTION_PERFORMANCE.PRODUCTION_ATTAINMENT as SUM(PRODUCED_QUANTITY) / NULLIF(SUM(PLANNED_QUANTITY), 0) with synonyms=('attainment rate','plan achievement','production yield','schedule adherence') comment='Ratio of actual to planned production.',
		PRODUCTION_PERFORMANCE.CONSTRAINED_PRODUCTION_DAYS as COUNT_IF(CONSTRAINT_FLAG = TRUE) with synonyms=('constraint count','days constrained','constrained days') comment='Count of constrained production-days.',
		PRODUCTION_PERFORMANCE.P104_EXPOSED_PRODUCTION_DAYS as COUNT_IF(P104_EXPOSURE_FLAG = TRUE) with synonyms=('p104 exposure count','p104 dependent days') comment='Count of production-days with P104 BOM dependency.',
		INVENTORY_POSITION.TOTAL_ON_HAND non additive by (INVENTORY_POSITION.SNAPSHOT_DATE asc nulls last) as SUM(ON_HAND_QUANTITY) with synonyms=('total inventory on hand','aggregate on hand','total stock','inventory on hand') comment='Sum of on-hand quantity. Semi-additive by snapshot_date.',
		INVENTORY_POSITION.TOTAL_AVAILABLE non additive by (INVENTORY_POSITION.SNAPSHOT_DATE asc nulls last) as SUM(AVAILABLE_QUANTITY) with synonyms=('total available stock','aggregate available','available inventory') comment='Sum of available quantity. Semi-additive by snapshot_date.',
		INVENTORY_POSITION.PARTS_BELOW_SAFETY_STOCK non additive by (INVENTORY_POSITION.SNAPSHOT_DATE asc nulls last) as COUNT_IF(BELOW_SAFETY_STOCK_FLAG = TRUE) with synonyms=('understocked parts','parts at risk','safety stock breaches') comment='Count of part-plant combos below safety stock. Semi-additive by snapshot_date.',
		SUPPLIER_PERFORMANCE.DEFECT_RATE as SUM(DEFECTIVE_QUANTITY) / NULLIF(SUM(INSPECTED_QUANTITY), 0) with synonyms=('quality defect rate','weighted defect rate','inspection failure rate') comment='Weighted defect rate from additive counts.',
		SUPPLIER_PERFORMANCE.REJECTION_RATE as SUM(REJECTED_QUANTITY) / NULLIF(SUM(RECEIVED_QUANTITY), 0) with synonyms=('weighted rejection rate','material rejection rate') comment='Weighted rejection rate from additive counts.'
	)
	comment='ChainLoom supply chain analytics semantic view. Provides five independent analytical surfaces plus a governed product-level risk signal summary. Each fact table is independently queryable with shared conformed dimensions (Date, Plant, Product, Part, Carrier). Fact-to-fact joins are intentionally not modeled to prevent fan-out and cross-grain aggregation errors. '
	ai_sql_generation 'CRITICAL RULES FOR CHAINLOOM ANALYTICS: 1. NO FACT-TO-FACT JOINS: Each analytical question must be answered from a SINGLE fact table joined only to dimension tables. Never join customer_fulfillment to shipment_performance, inventory_position to production_performance, or any other fact-to-fact combination. 2. INVENTORY IS SEMI-ADDITIVE: Inventory quantities can be summed across parts and plants for a SINGLE snapshot date, but MUST NOT be summed across multiple dates. For current inventory: WHERE SNAPSHOT_DATE = (SELECT MAX(SNAPSHOT_DATE) FROM CHAINLOOM.CURATED.V_INVENTORY_POSITION). For trends: GROUP BY SNAPSHOT_DATE. 3. NO BOM FAN-OUT: The Product-Part bill of materials is a many-to-many relationship NOT modeled in this semantic view. Do not traverse from products to parts through a BOM join. 4. NO SUPPLIER-PART FAN-OUT: The Supplier-Part sourcing table is NOT modeled here. supplier_performance already aggregates at the supplier-part grain. 5. SUPPLIER PERFORMANCE PRE-AGGREGATED RATIOS: AVG_RECEIPT_DELAY_DAYS, ON_TIME_RECEIPT_PCT, and DEFECT_RATE_PCT are pre-computed row-level ratios. Do NOT SUM or AVG these across rows. Use governed metrics (defect_rate, rejection_rate) for aggregates. 6. OBSERVED FACTS vs INFERENCE: Report only what the data directly shows. Do not infer root cause from constraints without explicit correlation analysis with caveats. 7. NO DETERMINISTIC SUPPLIER-TO-CUSTOMER CAUSALITY: ChainLoom does not contain lot/batch genealogy. Do not claim that a supplier delay caused a customer shipment delay. 8. P104 EXPOSURE does NOT equal P104 SHORTAGE: P104_EXPOSURE_FLAG indicates BOM dependency only. It does NOT prove P104 caused any production disruption. 9. ON-TIME DELIVERY CALCULATION: Uses DELIVERY_ELIGIBLE_FLAG = TRUE as denominator and ON_TIME_FLAG = TRUE as numerator. Never include in-transit or cancelled shipments. 10. ORDERED_QUANTITY DISAMBIGUATION: In customer_fulfillment it means quantity ordered BY customers. In supplier_performance it means quantity ordered FROM suppliers. 11. PRODUCT RISK SIGNALS ARE OBSERVATIONAL: The product_risk_signals table shows co-occurring risk indicators from independent surfaces. RISK_SIGNAL_COUNT counts how many surfaces show risk but does NOT establish that one risk caused another. Never claim fulfillment gaps caused delivery delays or that production constraints caused fulfillment shortfalls without explicit lot/batch evidence. '
	ai_verified_queries (
		Q1_FULFILLMENT_RATE_BY_SEGMENT AS (
QUESTION 'What is the fulfillment rate by customer segment?'
ONBOARDING_QUESTION false
SQL 'SELECT CUSTOMER_SEGMENT, SUM(FULFILLED_QUANTITY) / NULLIF(SUM(ORDERED_QUANTITY), 0) AS FULFILLMENT_RATE FROM __customer_fulfillment GROUP BY CUSTOMER_SEGMENT ORDER BY FULFILLMENT_RATE ASC'),
		Q2_FULFILLMENT_GAPS_BY_PRODUCT_FAMILY AS (
QUESTION 'Which product families have the most order lines with fulfillment gaps?'
ONBOARDING_QUESTION false
SQL 'SELECT PRODUCT_FAMILY, COUNT_IF(FULFILLMENT_GAP_FLAG = TRUE) AS ORDER_LINES_WITH_FULFILLMENT_GAPS FROM __customer_fulfillment GROUP BY PRODUCT_FAMILY ORDER BY ORDER_LINES_WITH_FULFILLMENT_GAPS DESC'),
		Q3_OTD_RATE_BY_CARRIER AS (
QUESTION 'What is the on-time delivery rate for each carrier?'
ONBOARDING_QUESTION false
SQL 'SELECT CARRIER_NAME, COUNT_IF(ON_TIME_FLAG = TRUE) / NULLIF(COUNT_IF(DELIVERY_ELIGIBLE_FLAG = TRUE), 0) AS ON_TIME_DELIVERY_RATE FROM __shipment_performance GROUP BY CARRIER_NAME ORDER BY ON_TIME_DELIVERY_RATE ASC'),
		Q4_AVG_DELAY_BY_PRIORITY AS (
QUESTION 'What is the average delivery delay in days for each customer priority tier?'
ONBOARDING_QUESTION false
SQL 'SELECT CUSTOMER_PRIORITY, AVG(CASE WHEN DELIVERY_ELIGIBLE_FLAG = TRUE THEN DELIVERY_DELAY_DAYS END) AS AVG_DELIVERY_DELAY_DAYS FROM __shipment_performance GROUP BY CUSTOMER_PRIORITY ORDER BY AVG_DELIVERY_DELAY_DAYS DESC'),
		Q5_PRODUCTION_ATTAINMENT_BY_PLANT AS (
QUESTION 'What is the production attainment rate for each plant?'
ONBOARDING_QUESTION false
SQL 'SELECT PLANT_NAME, SUM(PRODUCED_QUANTITY) / NULLIF(SUM(PLANNED_QUANTITY), 0) AS PRODUCTION_ATTAINMENT FROM __production_performance GROUP BY PLANT_NAME ORDER BY PRODUCTION_ATTAINMENT ASC'),
		Q6_CONSTRAINED_DAYS_P104_EXPOSED AS (
QUESTION 'How many constrained production days occurred for products that depend on Part P104?'
ONBOARDING_QUESTION false
SQL 'SELECT PRODUCT_NAME, COUNT_IF(CONSTRAINT_FLAG = TRUE) AS CONSTRAINED_PRODUCTION_DAYS, COUNT(*) AS TOTAL_PRODUCTION_DAYS FROM __production_performance WHERE P104_EXPOSURE_FLAG = TRUE GROUP BY PRODUCT_NAME ORDER BY CONSTRAINED_PRODUCTION_DAYS DESC'),
		Q7_PARTS_BELOW_SAFETY_STOCK_CURRENT AS (
QUESTION 'How many parts are currently below safety stock at each plant?'
ONBOARDING_QUESTION false
SQL 'SELECT PLANT_NAME, COUNT_IF(BELOW_SAFETY_STOCK_FLAG = TRUE) AS PARTS_BELOW_SAFETY_STOCK FROM __inventory_position WHERE SNAPSHOT_DATE = (SELECT MAX(SNAPSHOT_DATE) FROM __inventory_position) GROUP BY PLANT_NAME ORDER BY PARTS_BELOW_SAFETY_STOCK DESC'),
		Q8_INVENTORY_TREND_BY_DATE AS (
QUESTION 'Show the total available inventory quantity for each snapshot date.'
ONBOARDING_QUESTION false
SQL 'SELECT SNAPSHOT_DATE, SUM(AVAILABLE_QUANTITY) AS TOTAL_AVAILABLE FROM __inventory_position GROUP BY SNAPSHOT_DATE ORDER BY SNAPSHOT_DATE'),
		Q9_DEFECT_RATE_BY_SUPPLIER_TIER AS (
QUESTION 'What is the defect rate for each supplier tier?'
ONBOARDING_QUESTION false
SQL 'SELECT SUPPLIER_TIER, SUM(DEFECTIVE_QUANTITY) / NULLIF(SUM(INSPECTED_QUANTITY), 0) AS DEFECT_RATE FROM __supplier_performance GROUP BY SUPPLIER_TIER ORDER BY DEFECT_RATE DESC'),
		Q10_SUPPLIERS_HIGH_RECEIPT_DELAY AS (
QUESTION 'Which suppliers have an average receipt delay greater than 2 days?'
ONBOARDING_QUESTION false
SQL 'SELECT SUPPLIER_NAME, PART_NAME, AVG_RECEIPT_DELAY_DAYS, SUPPLY_RISK_BAND FROM __supplier_performance WHERE AVG_RECEIPT_DELAY_DAYS > 2 ORDER BY AVG_RECEIPT_DELAY_DAYS DESC'),
		Q13_MULTI_SIGNAL_PRODUCT_RISK AS (
QUESTION 'Which products currently show multiple independent supply-chain risk signals across fulfillment, delivery, and production?'
ONBOARDING_QUESTION false
SQL 'SELECT PRODUCT_NAME, FULFILLMENT_RATE, ON_TIME_DELIVERY_RATE, PRODUCTION_ATTAINMENT, RISK_SIGNAL_COUNT, FULFILLMENT_RISK_FLAG, DELIVERY_RISK_FLAG, PRODUCTION_RISK_FLAG FROM __product_risk_signals WHERE RISK_SIGNAL_COUNT >= 2 ORDER BY RISK_SIGNAL_COUNT DESC, PRODUCTION_ATTAINMENT ASC')
	)
	with extension (CA='{"tables":[{"name":"customer_fulfillment","dimensions":[{"name":"order_line_id"},{"name":"order_id"},{"name":"order_date"},{"name":"promised_date"},{"name":"customer_id"},{"name":"customer_name"},{"name":"customer_segment"},{"name":"customer_region"},{"name":"customer_priority"},{"name":"product_id"},{"name":"product_name"},{"name":"product_family"},{"name":"product_category"},{"name":"plant_id"},{"name":"plant_name"},{"name":"plant_region"},{"name":"order_status"},{"name":"fulfillment_gap_flag"}],"facts":[{"name":"ordered_quantity"},{"name":"fulfilled_quantity"},{"name":"unfulfilled_quantity"}],"metrics":[{"name":"fulfillment_rate","data_type":"NUMBER"},{"name":"order_lines_with_fulfillment_gaps","data_type":"NUMBER"}]},{"name":"shipment_performance","dimensions":[{"name":"shipment_id"},{"name":"order_line_id"},{"name":"customer_id"},{"name":"customer_name"},{"name":"customer_segment"},{"name":"customer_region"},{"name":"customer_priority"},{"name":"product_id"},{"name":"product_name"},{"name":"product_family"},{"name":"plant_id"},{"name":"plant_name"},{"name":"plant_region"},{"name":"carrier_id"},{"name":"carrier_name"},{"name":"service_level"},{"name":"ship_date"},{"name":"promised_date"},{"name":"actual_delivery_date"},{"name":"shipment_status"},{"name":"delay_reason"},{"name":"on_time_flag"},{"name":"delivery_eligible_flag"}],"facts":[{"name":"shipped_quantity"},{"name":"delivery_delay_days"}],"metrics":[{"name":"on_time_delivery_rate","data_type":"NUMBER"},{"name":"avg_delivery_delay_days","data_type":"NUMBER"}]},{"name":"production_performance","dimensions":[{"name":"production_id"},{"name":"production_date"},{"name":"plant_id"},{"name":"plant_name"},{"name":"plant_region"},{"name":"product_id"},{"name":"product_name"},{"name":"product_family"},{"name":"product_category"},{"name":"production_status"},{"name":"constraint_flag"},{"name":"critical_part_count"},{"name":"critical_parts"},{"name":"p104_exposure_flag"},{"name":"p104_qty_per_product"}],"facts":[{"name":"planned_quantity"},{"name":"produced_quantity"},{"name":"production_gap_quantity"},{"name":"downtime_hours"}],"metrics":[{"name":"production_attainment","data_type":"NUMBER"},{"name":"constrained_production_days","data_type":"NUMBER"},{"name":"p104_exposed_production_days","data_type":"NUMBER"}]},{"name":"inventory_position","dimensions":[{"name":"inventory_snapshot_id"},{"name":"snapshot_date"},{"name":"part_id"},{"name":"part_name"},{"name":"part_category"},{"name":"criticality"},{"name":"plant_id"},{"name":"plant_name"},{"name":"plant_region"},{"name":"below_safety_stock_flag"},{"name":"inventory_risk_band"}],"facts":[{"name":"on_hand_quantity"},{"name":"reserved_quantity"},{"name":"available_quantity"},{"name":"safety_stock_quantity"},{"name":"safety_stock_gap"}],"metrics":[{"name":"total_on_hand","data_type":"NUMBER"},{"name":"total_available","data_type":"NUMBER"},{"name":"parts_below_safety_stock","data_type":"NUMBER"}]},{"name":"supplier_performance","dimensions":[{"name":"supplier_id"},{"name":"supplier_name"},{"name":"supplier_region"},{"name":"supplier_tier"},{"name":"supplier_status"},{"name":"part_id"},{"name":"part_name"},{"name":"part_category"},{"name":"criticality"},{"name":"preferred_supplier_flag"},{"name":"allocation_percent"},{"name":"supply_risk_band"},{"name":"avg_receipt_delay_days"},{"name":"on_time_receipt_pct"},{"name":"defect_rate_pct"}],"facts":[{"name":"po_line_count"},{"name":"ordered_quantity"},{"name":"receipt_count"},{"name":"received_quantity"},{"name":"accepted_quantity"},{"name":"rejected_quantity"},{"name":"inspected_quantity"},{"name":"defective_quantity"}],"metrics":[{"name":"defect_rate","data_type":"NUMBER"},{"name":"rejection_rate","data_type":"NUMBER"}]},{"name":"product_risk_signals","dimensions":[{"name":"product_id"},{"name":"product_name"},{"name":"fulfillment_risk_flag"},{"name":"delivery_risk_flag"},{"name":"production_risk_flag"},{"name":"risk_signal_count"}],"facts":[{"name":"fulfillment_rate"},{"name":"on_time_delivery_rate"},{"name":"production_attainment"},{"name":"order_lines_with_gaps"},{"name":"eligible_shipments"},{"name":"constrained_days"},{"name":"total_production_days"}]},{"name":"date_dim","dimensions":[{"name":"date_key"},{"name":"calendar_date"},{"name":"year"},{"name":"quarter"},{"name":"month"},{"name":"month_name"},{"name":"week_of_year"},{"name":"day_of_week"},{"name":"day_name"},{"name":"is_weekend"}]},{"name":"plant","dimensions":[{"name":"plant_id"},{"name":"plant_code"},{"name":"plant_name"},{"name":"city"},{"name":"region"},{"name":"plant_type"},{"name":"capacity_units_per_day"}]},{"name":"product","dimensions":[{"name":"product_id"},{"name":"product_code"},{"name":"product_name"},{"name":"product_family"},{"name":"product_category"},{"name":"unit_price"}]},{"name":"part","dimensions":[{"name":"part_id"},{"name":"part_code"},{"name":"part_name"},{"name":"part_category"},{"name":"unit_of_measure"},{"name":"criticality"},{"name":"standard_cost"}]},{"name":"carrier","dimensions":[{"name":"carrier_id"},{"name":"carrier_code"},{"name":"carrier_name"},{"name":"service_level"},{"name":"carrier_region"}]}],"relationships":[{"name":"fulfillment_to_date"},{"name":"fulfillment_to_plant"},{"name":"fulfillment_to_product"},{"name":"shipment_to_date"},{"name":"shipment_to_plant"},{"name":"shipment_to_product"},{"name":"shipment_to_carrier"},{"name":"production_to_date"},{"name":"production_to_plant"},{"name":"production_to_product"},{"name":"inventory_to_date"},{"name":"inventory_to_plant"},{"name":"inventory_to_part"},{"name":"supplier_to_part"}]}');
