# ChainLoom — Governed Metrics

**Status:** Architecture Approved / Model Hardened
**Version:** 1.1
**Problem Statement:** Supply Chain Ontology and Governed Conversational Analytics

## 1. Purpose

This document defines the business meaning, calculation logic, grain and interpretation of ChainLoom's governed metrics.

## 2. Metric Design Principles

1. One canonical definition.
2. Explicit eligibility.
3. Explicit grain.
4. No accidental double counting.
5. Explicit analysis period.
6. Explainable calculation.
7. Evidence-backed results.
8. AI does not invent formulas.

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

```text
On-Time Delivery Rate
=
On-Time Eligible Shipments
/
Eligible Delivered Shipments
× 100
```

Eligible shipment: promised and actual delivery dates exist, shipment is not cancelled, and it belongs to the requested period.

**Grain:** Shipment.

## 5. M02 — Late Shipment Count

```text
COUNT(shipments)
WHERE actual_delivery_date > promised_date
```

**Grain:** Shipment.

## 6. M03 — Fill Rate

```text
Fill Rate
=
SUM(fulfilled_quantity)
/
SUM(ordered_quantity)
× 100
```

**Grain:** Order Line.

Do not calculate after an uncontrolled one-to-many shipment join.

## 7. M04 — Average Supplier Lead Time

**Definition:** Average elapsed time from purchase-order line creation to actual receipt for eligible completed supplier commitments.

```text
AVG(DATEDIFF('day', order_date, receipt_date))
```

**Grain:** Eligible receipt / PO-line fulfillment event.

This is a relationship metric between PO Line and Supply Receipt.

## 8. M05 — Supplier Inbound On-Time Rate

```text
Supplier Inbound On-Time Rate
=
On-Time Supply Receipts
/
Eligible Supply Receipts
× 100
```

On-time: `receipt_date <= promised_receipt_date`.

**Grain:** Supply Receipt.

## 9. M06 — Supplier Defect Rate

```text
Supplier Defect Rate
=
SUM(defective_quantity)
/
SUM(inspected_quantity)
× 100
```

**Grain:** Quality Inspection.

## 10. M07 — Inventory Coverage Days

```text
Inventory Coverage Days
=
Available Inventory
/
Average Daily Demand
```

**Grain:** Part × Plant × Snapshot Date.

Initial demand window: previous 30 days.

If average daily demand is zero, return NULL.

Inventory is semi-additive across time. Current inventory uses the latest appropriate snapshot rather than summing daily snapshots.

## 11. M08 — At-Risk Order Count

```text
COUNT(DISTINCT order_line_id)
WHERE
order_status is open
AND projected_fulfillment_date > promised_date
```

**Grain:** Order Line.

The projected date is deterministic and must not be described as an AI-generated forecast.

## 12. M09 — At-Risk Shipment Count

Number of shipments associated with order lines classified as at risk.

**Grain:** Shipment.

## 13. M10 — Confirmed Impacted Customer Count

Number of distinct customers associated with observed delayed shipments.

```text
COUNT(DISTINCT customer_id)
```

This represents observed impact.

## 14. M11 — At-Risk Customer Count

Number of distinct customers associated with open order lines meeting deterministic ChainLoom risk criteria.

```text
COUNT(DISTINCT customer_id)
```

This represents potential risk.

## 15. Supplier Attribution Rules

Capability:
Supplier → Supplier-Part → Part

Commitment:
Supplier → PO Line → Part → Plant

Actual supply:
Supplier → Supply Receipt → Part → Plant

Capability is not actual supply. Actual supply is not proof of exact downstream causality without material genealogy.

## 16. Inventory Rules

Never sum daily inventory snapshots to answer a point-in-time inventory question.

The semantic layer must treat the inventory measure as semi-additive across time.

## 17. Metric Anti-Patterns

Avoid:
- Fact-to-fact fan-out
- Undefined denominators
- Hidden filters
- Multiple definitions for one metric
- AI-invented formulas
- Ambiguous supplier attribution
- Unsupported causal claims
- Summing inventory across snapshot dates

## 18. Investigation Outputs

Analytical conclusions include:
- Supplier contribution to OTD deterioration
- Plant contribution to delay increase
- Customer impact severity
- Disruption propagation path

These derive from governed metrics and facts.

## 19. Metric Acceptance Criteria

A metric is implementation-ready when definition, formula, eligibility, grain, dimensions, edge cases and test examples are explicit and can be represented consistently in the Semantic View.
