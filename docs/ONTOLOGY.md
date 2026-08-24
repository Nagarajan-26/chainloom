# ChainLoom — Supply Chain Ontology

**Status:** Architecture Approved  
**Version:** 1.0  
**Problem Statement:** Supply Chain Ontology and Governed Conversational Analytics

## 1. Purpose

The ChainLoom ontology defines the business entities, relationships and business concepts required to understand supply-chain performance and trace operational impact across the supply network.

The ontology is the conceptual foundation for:
- Snowflake curated data
- Snowflake Semantic Views
- Cortex Analyst
- Investigation workflows
- Impact analysis
- Governed metrics
- Golden-question evaluation

The ontology describes business meaning independently from the physical database implementation.

## 2. Core Business Flow

Supplier → Part → Product → Plant → Inventory / Production → Customer Order → Shipment → Customer

Primary disruption path:

Supplier disruption → Part availability impact → Inventory depletion → Production constraint → Order fulfillment impact → Shipment delay → Customer impact

## 3. Business Entities

### 3.1 Supplier
**Grain:** One row per supplier.  
**Primary key:** `supplier_id`

Key attributes:
- supplier_id
- supplier_name
- supplier_region
- supplier_tier
- supplier_status
- risk_class
- created_date

### 3.2 Part
**Grain:** One row per part.  
**Primary key:** `part_id`

Key attributes:
- part_id
- part_name
- part_category
- criticality
- unit_cost
- uom
- status

### 3.3 Product
**Grain:** One row per product.  
**Primary key:** `product_id`

Key attributes:
- product_id
- product_name
- product_category
- unit_price
- status

### 3.4 Plant
**Grain:** One row per plant.  
**Primary key:** `plant_id`

Key attributes:
- plant_id
- plant_name
- city
- region
- capacity_units_per_day
- status

### 3.5 Customer
**Grain:** One row per customer.  
**Primary key:** `customer_id`

Key attributes:
- customer_id
- customer_name
- customer_segment
- region
- priority_tier
- status

### 3.6 Carrier
**Grain:** One row per carrier.  
**Primary key:** `carrier_id`

Key attributes:
- carrier_id
- carrier_name
- service_level
- region
- status

## 4. Business Facts

### 4.1 Supply Receipt
**Definition:** Inbound material received from a specific supplier for a specific part at a specific plant.

**Grain:** One row per supplier-part receipt event at a plant.  
**Primary key:** `receipt_id`

Key attributes:
- receipt_id
- supplier_id
- part_id
- plant_id
- receipt_date
- expected_date
- received_quantity
- accepted_quantity
- rejected_quantity
- receipt_status
- purchase_reference

This fact establishes actual supplier-to-plant supply provenance.

### 4.2 Order Line
**Grain:** One row per customer order line.  
**Primary key:** `order_line_id`

Key attributes:
- order_line_id
- order_id
- customer_id
- product_id
- plant_id
- order_date
- promised_date
- ordered_quantity
- fulfilled_quantity
- order_status

### 4.3 Shipment
**Grain:** One row per shipment against an order line.  
**Primary key:** `shipment_id`

Key attributes:
- shipment_id
- order_line_id
- carrier_id
- plant_id
- ship_date
- promised_date
- actual_delivery_date
- shipped_quantity
- shipment_status
- delay_reason

### 4.4 Inventory Snapshot
**Grain:** One row per Part × Plant × Snapshot Date.  
**Logical key:** `part_id + plant_id + snapshot_date`

Key attributes:
- inventory_snapshot_id
- part_id
- plant_id
- snapshot_date
- on_hand_quantity
- reserved_quantity
- available_quantity
- incoming_quantity

### 4.5 Production
**Grain:** One row per Plant × Product × Production Date.  
**Primary key:** `production_id`

Key attributes:
- production_id
- plant_id
- product_id
- production_date
- planned_quantity
- produced_quantity
- downtime_hours
- production_status

### 4.6 Quality Inspection
**Grain:** One row per quality inspection event.  
**Primary key:** `inspection_id`

Key attributes:
- inspection_id
- supplier_id
- part_id
- plant_id
- inspection_date
- inspected_quantity
- defective_quantity
- defect_type

## 5. Relationship Entities

### 5.1 Supplier-Part
One row per Supplier × Part sourcing relationship.

Logical key: `supplier_id + part_id`

Attributes:
- supplier_id
- part_id
- lead_time_days
- minimum_order_qty
- preferred_supplier_flag
- supplier_part_status
- effective_date
- end_date

Supplier ↔ Part is many-to-many.

This establishes capability, not proof of actual supply.

### 5.2 Product-Part
One row per Product × Part BOM relationship.

Logical key: `product_id + part_id`

Attributes:
- product_id
- part_id
- quantity_per_product
- critical_component_flag
- effective_date
- end_date

Product ↔ Part is many-to-many.

### 5.3 Date
One row per calendar date.

Primary key: `date_key`

Attributes:
- date_key
- calendar_date
- day_of_week
- week_number
- month
- month_name
- quarter
- year
- is_weekend

## 6. Relationship Map

```text
                         SUPPLIER
                            │
                    actual supply
                            │
                            ▼
                    SUPPLY RECEIPT
                            │
                            ▼
                          PART
                            │
                     used in / BOM
                            │
                            ▼
                         PRODUCT
                            │
                      manufactured
                            │
                            ▼
                          PLANT
                         /                             /                        INVENTORY     PRODUCTION
                      │            │
                      └─────┬──────┘
                            │
                            ▼
                       ORDER LINE
                            │
                            ▼
                        SHIPMENT
                       /                              /                           CARRIER       CUSTOMER
```

Capability:
`SUPPLIER ←→ PART` through `BRIDGE_SUPPLIER_PART`.

Product dependency:
`PRODUCT ←→ PART` through `BRIDGE_PRODUCT_PART`.

## 7. Critical Multi-Hop Relationships

Capability path:

Supplier → Supplier-Part → Part → Product-Part → Product → Order Line → Customer

Operational impact path:

Supplier → Supply Receipt → Part → Plant → Inventory / Production → Order Line → Shipment → Customer

Relationship traversal alone does not establish customer impact. Current business state must be considered.

## 8. Confirmed Impact vs Potential Risk

**Confirmed impact:** A customer has an observed delayed shipment.

**Potential risk:** A customer has an open order that meets deterministic ChainLoom risk criteria.

These categories must not be merged.

## 9. Ontology Design Principles

1. Business meaning first.
2. Every fact has explicit grain.
3. Many-to-many relationships use explicit bridges.
4. Actual supply is distinct from supplier capability.
5. Relationship traversal does not automatically establish causality.
6. Current business state matters.
7. Semantic exposure should be simpler than the full physical model.
8. AI must not invent unsupported relationships.

## 10. Core Impact Path

```text
Supplier disruption
        ↓
Affected Part
        ↓
Supply / Inventory position
        ↓
Production constraint
        ↓
Open Customer Demand
        ↓
Shipment / Fulfillment
        ↓
Customer Impact
```

## 11. Initial Controlled Scenario

The initial synthetic environment contains a deliberate supplier disruption centered around Supplier S017:

S017 lead time deteriorates → P104 supply receipts become delayed → P104 inventory declines at PL03 → production availability decreases → open orders become exposed → shipments miss promised dates → customers become impacted or at risk.

Exact values will be defined during synthetic-data generation.

## 12. Semantic Boundary

The conceptual ontology is richer than the initial conversational semantic model.

The semantic model should prioritize:
- Supplier
- Part
- Product
- Plant
- Inventory
- Supply Receipt
- Customer
- Order
- Shipment
- Carrier

Implementation-specific identifiers and unnecessary physical columns should not automatically become business-facing concepts.

## 13. Future Extensions

Potential future entities:
- Warehouse
- Route
- Port
- Purchase Order
- Return
- Contract
- Logistics Hub
- Sensor / IoT Event

These remain outside the initial MVP unless justified.

## 14. Acceptance Criteria

The ontology is ready when:
- Core entities have unambiguous definitions.
- Every fact has explicit grain.
- Many-to-many relationships are explicit.
- Supplier capability and actual supply are distinguished.
- Multi-hop paths are logically valid.
- Metrics can be computed without unintended double counting.
- Synthetic data can support intended scenarios.
- The semantic layer can expose useful concepts without unnecessary physical complexity.
