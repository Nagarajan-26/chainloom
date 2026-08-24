# ChainLoom — Governed Metrics

**Status:** Architecture Approved  
**Version:** 1.0  
**Problem Statement:** Supply Chain Ontology and Governed Conversational Analytics

## 1. Purpose

This document defines the business meaning, calculation logic, grain and interpretation of ChainLoom's governed supply-chain metrics.

A metric must have one authoritative definition across Snowflake Semantic Views, SQL, Cortex Analyst, Cortex Agent workflows, Streamlit, evaluation and documentation.

## 2. Metric Design Principles

1. One canonical definition.
2. Explicit eligibility.
3. Explicit underlying grain.
4. No accidental double counting.
5. Explicit analysis period.
6. Explainable calculation.
7. Evidence-backed results.
8. AI does not invent metric formulas.

## 3. Metric Catalogue

1. On-Time Delivery Rate
2. Late Shipment Count
3. Fill Rate
4. Average Supplier Lead Time
5. Supplier Inbound On-Time Rate
6. Supplier Defect Rate
7. Inventory Coverage Days
8. At-Risk Order Count
9. At-Risk Shipment Count
10. Confirmed Impacted Customer Count
11. At-Risk Customer Count

## 4. M01 — On-Time Delivery Rate

**Definition:** Percentage of eligible delivered shipments whose actual delivery date is on or before the promised delivery date.

```text
On-Time Delivery Rate
=
On-Time Eligible Shipments
/
Eligible Delivered Shipments
× 100
```

Numerator: eligible delivered shipments where `actual_delivery_date <= promised_delivery_date`.

Denominator: eligible delivered shipments.

Eligibility:
- shipment exists
- promised delivery date exists
- actual delivery date exists
- shipment is not cancelled
- shipment belongs to requested analysis period

**Grain:** Shipment.

Useful dimensions:
- Supplier
- Part
- Product
- Plant
- Customer
- Carrier
- Region
- Date

## 5. M02 — Late Shipment Count

**Definition:** Number of eligible delivered shipments whose actual delivery date is later than promised.

```text
COUNT(shipments)
WHERE actual_delivery_date > promised_delivery_date
```

**Grain:** Shipment.

## 6. M03 — Fill Rate

**Definition:** Percentage of ordered quantity that has been fulfilled.

```text
Fill Rate
=
SUM(fulfilled_quantity)
/
SUM(ordered_quantity)
× 100
```

Eligibility: valid non-cancelled order lines.

**Grain:** Order Line.

Do not calculate after joining to multiple shipment rows unless shipment quantities have first been safely aggregated to order-line grain.

## 7. M04 — Average Supplier Lead Time

**Definition:** Average expected supplier lead time across active Supplier-Part relationships.

```text
AVG(lead_time_days)
```

**Grain:** Supplier-Part relationship.

Eligibility: active supplier, active part, active sourcing relationship.

## 8. M05 — Supplier Inbound On-Time Rate

**Definition:** Percentage of eligible supplier receipts received on or before expected receipt date.

```text
Supplier Inbound On-Time Rate
=
On-Time Supply Receipts
/
Eligible Supply Receipts
× 100
```

Numerator: receipts where `receipt_date <= expected_date`.

Denominator: eligible receipts with valid expected and actual receipt dates.

**Grain:** Supply Receipt.

Useful dimensions:
- Supplier
- Part
- Plant
- Region
- Date

## 9. M06 — Supplier Defect Rate

**Definition:** Percentage of inspected quantity found defective.

```text
Supplier Defect Rate
=
SUM(defective_quantity)
/
SUM(inspected_quantity)
× 100
```

Eligibility: valid inspection with `inspected_quantity > 0`.

**Grain:** Quality Inspection.

## 10. M07 — Inventory Coverage Days

**Definition:** Estimated number of days currently available inventory can support expected daily demand.

```text
Inventory Coverage Days
=
Available Inventory
/
Average Daily Demand
```

**Grain:** Part × Plant × Snapshot Date.

Initial demand window: previous 30 days.

If average daily demand is zero, return NULL rather than infinity.

## 11. M08 — At-Risk Order Count

**Definition:** Number of open order lines whose deterministic projected fulfillment date exceeds the promised delivery date.

```text
COUNT(DISTINCT order_line_id)
WHERE
order_status is open
AND projected_fulfillment_date > promised_date
```

**Grain:** Order Line.

`projected_fulfillment_date` is a derived business concept and must be deterministic. It must not be presented as an AI-generated operational forecast.

## 12. M09 — At-Risk Shipment Count

**Definition:** Number of shipments associated with order lines classified as at risk.

**Grain:** Shipment.

A shipment is counted once.

## 13. M10 — Confirmed Impacted Customer Count

**Definition:** Number of distinct customers associated with an observed delayed shipment.

```text
COUNT(DISTINCT customer_id)
```

over the confirmed-impact population.

This represents observed impact, not prediction.

## 14. M11 — At-Risk Customer Count

**Definition:** Number of distinct customers associated with open order lines that meet deterministic ChainLoom risk criteria.

```text
COUNT(DISTINCT customer_id)
```

over the at-risk order population.

This represents potential risk, not confirmed impact.

## 15. Supplier Attribution Rules

Supplier capability:

```text
Supplier
→ BRIDGE_SUPPLIER_PART
→ Part
```

means the supplier can provide the part.

Actual supply:

```text
Supplier
→ FACT_SUPPLY_RECEIPT
→ Part
→ Plant
```

means the supplier actually supplied material.

Supplier-Part capability must never be treated as proof that the supplier caused a downstream shipment delay.

Without material-allocation/lot-level data, ChainLoom must not claim exact shipment-to-supplier causality.

## 16. Metric Dependency Graph

```text
SHIPMENT
   │
   ├── On-Time Delivery Rate
   └── Late Shipment Count

ORDER LINE
   │
   └── Fill Rate

SUPPLIER-PART
   │
   └── Average Supplier Lead Time

SUPPLY RECEIPT
   │
   └── Supplier Inbound On-Time Rate

QUALITY
   │
   └── Supplier Defect Rate

INVENTORY + DEMAND
   │
   └── Inventory Coverage Days

ORDER + SUPPLY + INVENTORY
   │
   └── At-Risk Orders

AT-RISK ORDERS
   │
   ├── At-Risk Shipments
   └── At-Risk Customers

DELAYED SHIPMENTS
   │
   └── Confirmed Impacted Customers
```

## 17. Metric Anti-Patterns

Avoid:
- Double-counting through fact-to-fact joins.
- Undefined denominators.
- Hidden filters.
- Different definitions for the same metric.
- AI-invented formulas.
- Ambiguous supplier attribution.
- Unsupported causal claims.
- Exact-looking risk numbers unsupported by deterministic rules.

## 18. Investigation Outputs

These are analytical conclusions rather than independent base metrics:
- Supplier contribution to OTD decline
- Plant contribution to delay increase
- Customer impact severity
- Disruption propagation path

They should be derived from governed base metrics and underlying facts.

## 19. Metric Acceptance Criteria

A metric is implementation-ready when:
- Definition is unambiguous.
- Formula is explicit.
- Numerator and denominator are known where applicable.
- Eligibility is defined.
- Grain is known.
- Valid dimensions are identified.
- Double-counting risks are addressed.
- Edge cases are documented.
- A deterministic test example can be created.
- The metric can be represented consistently in the Semantic View.
