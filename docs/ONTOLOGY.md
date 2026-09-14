# ChainLoom — Supply Chain Ontology

**Status:** Implemented
**Version:** 2.0
**Problem Statement:** Supply Chain Ontology and Governed Conversational Analytics

## 1. Purpose

The ontology defines business entities, relationships and concepts required to understand supply-chain performance and trace operational impact.

## 2. Core Business Flow

Supplier → Part → Product → Plant → Inventory / Production → Customer Order → Shipment → Customer

Primary dependency path (as represented in the deterministic synthetic dataset):

Supplier disruption → Part availability impact → Inventory deterioration → Production constraint → Order fulfillment impact → Shipment delay → Customer impact

This path describes the operational dependency sequence embedded in the synthetic scenario. It does not establish that each step caused the next — relationship traversal does not automatically establish causality (see section 9).

## 3. Business Entities

### Supplier
One row per supplier. Primary key: `supplier_id`.

### Part
One row per part. Primary key: `part_id`.

### Product
One row per product. Primary key: `product_id`.

### Plant
One row per plant. Primary key: `plant_id`.

For the MVP, Plant is also the inventory location grain. No separate Warehouse/Storage Location entity is required.

### Customer
One row per customer. Primary key: `customer_id`.

Customer is the terminal customer entity for the MVP.

### Carrier
One row per carrier. Primary key: `carrier_id`.

Explicit relationship: Shipment → Carrier.

### Date
One row per calendar date. Primary key: `date_key`.

Each fact uses its relevant date role: receipt, production, order, ship or inspection date.

## 4. Procurement and Supply Facts

### Purchase Order Line

**Definition:** Supplier commitment for a specific part and plant.

**Grain:** One row per purchase-order line.

**Primary key:** `po_line_id`

Key fields:
- po_line_id
- po_id
- supplier_id
- part_id
- plant_id
- order_date
- promised_receipt_date
- ordered_quantity
- po_line_status

### Supply Receipt

**Definition:** Actual inbound material receipt.

**Grain:** One row per receipt event / receipt line.

**Primary key:** `receipt_id`

Key fields:
- receipt_id
- po_line_id
- supplier_id
- part_id
- plant_id
- receipt_date
- received_quantity
- accepted_quantity
- rejected_quantity
- receipt_status

PO Line provides commitment; Supply Receipt provides actual receipt.

## 5. Operational Facts

### Inventory Snapshot

**Grain:** One row per Part × Plant × Snapshot Date.

Inventory is point-in-time and semi-additive.

### Production

**Grain:** One row per Plant × Product × Production Date.

This represents production output, not a production-order header.

### Order Line

**Grain:** One row per customer order line.

Primary key: `order_line_id`.

### Shipment

**Grain:** One row per shipment event.

Primary key: `shipment_id`.

The MVP assumes one shipment is associated with one order line. If consolidated shipments are introduced later, a shipment-line bridge will be added.

### Quality Inspection

**Grain:** One row per Supplier × Part × Plant quality inspection event.

Primary key: `inspection_id`.

Quality inspection is not production-batch genealogy.

## 6. Relationship Entities

### Supplier-Part

One row per Supplier × Part sourcing relationship.

This establishes supplier capability, not actual supply.

### Product-Part

One row per Product × Part BOM relationship.

This is many-to-many and is represented by a bridge.

## 7. Relationship Map

```text
                         SUPPLIER
                         /                              /                     capability          commitment
                      /                                 ▼              ▼
              SUPPLIER-PART      PO LINE
                     │              │
                     │              ▼
                     │        SUPPLY RECEIPT
                     │              │
                     └──────► PART ◄┘
                                │
                           PRODUCT-PART
                                │
                                ▼
                             PRODUCT
                            /                                  /                             PRODUCTION     ORDER LINE
                         │              │
                         │              ▼
                         │           SHIPMENT
                         │          /                                │         ▼         ▼
                         │      CARRIER   CUSTOMER
                         │
                         ▼
                       PLANT
                      /                          ▼       ▼
                INVENTORY   QUALITY
```

## 8. Critical Multi-Hop Relationships

Capability:
Supplier → Supplier-Part → Part → Product-Part → Product → Order Line → Customer

Operational impact:
Supplier → PO Line → Supply Receipt → Part → Plant → Inventory / Production → Product / Order Line → Shipment → Customer

## 9. Supplier Attribution Boundary

The MVP deliberately does not implement:
- Lot-level inventory
- Material allocation
- Production-batch genealogy
- FIFO/LIFO consumption tracing

Therefore ChainLoom must not claim:

> Receipt R123 definitively caused Shipment S456.

It may state that supplier performance deteriorated along an observed operational dependency path.

## 10. Confirmed Impact vs Potential Risk

**Confirmed impact:** observed delayed shipment linked to a customer.

**Potential risk:** open demand meeting deterministic ChainLoom risk conditions.

These populations must not be merged.

## 11. Ontology Design Principles

1. Business meaning first.
2. Every fact has explicit grain.
3. Many-to-many relationships use bridge tables.
4. Actual supply is distinct from supplier capability.
5. Purchase commitments are distinct from actual receipts.
6. Inventory is point-in-time and semi-additive.
7. Relationship traversal does not automatically establish causality.
8. Semantic exposure should be simpler than the physical model.
9. AI must not invent unsupported relationships.
10. Ambiguous relationship paths must be controlled in the semantic layer.

## 12. Physical, Curated and Semantic Layers

The ontology is realized across three layers:

### RAW Layer (Physical Entities)

16 tables in `CHAINLOOM.RAW`: DATE_DIM, SUPPLIER, PART, PRODUCT, PLANT, CUSTOMER, CARRIER, SUPPLIER_PART, PRODUCT_PART, PURCHASE_ORDER_LINE, SUPPLY_RECEIPT, INVENTORY, PRODUCTION, QUALITY, ORDER_LINE, SHIPMENT.

These use plain names (no `DIM_`, `FACT_`, or `BRIDGE_` prefixes).

### CURATED Layer (Analytical Surfaces)

6 views in `CHAINLOOM.CURATED` that join RAW facts with RAW dimensions into self-contained analytical surfaces:

| View | Grain |
|------|-------|
| V_SUPPLIER_PERFORMANCE | Supplier × Part |
| V_INVENTORY_POSITION | Part × Plant × Snapshot Date |
| V_PRODUCTION_PERFORMANCE | Plant × Product × Production Date |
| V_CUSTOMER_FULFILLMENT | Order Line |
| V_SHIPMENT_PERFORMANCE | Shipment |
| V_PRODUCT_RISK_SIGNALS | Product (synthesized from three surfaces above) |

### SEMANTIC Layer (Logical Tables)

`CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS` exposes 11 logical tables: the 6 curated surfaces plus 5 RAW dimension tables (DATE_DIM, PLANT, PRODUCT, PART, CARRIER). The semantic view adds 14 fact-to-dimension relationships, 12 governed metrics, synonyms, business comments, and AI generation instructions.

SUPPLIER and CUSTOMER are not registered as standalone dimension tables in the semantic view — their attributes are denormalized into the curated fact views.

## 13. Acceptance Criteria

The ontology is ready when:
- Core entities have unambiguous definitions.
- Every fact has explicit grain.
- Many-to-many relationships are explicit.
- Supplier capability and actual supply are distinguished.
- Purchase commitment and actual receipt are distinguished.
- Multi-hop paths are logically valid.
- Metrics can be computed without unintended double counting.
- Synthetic data supports intended scenarios.
- Semantic exposure remains focused.
