# ChainLoom — Governed Metrics

**Version:** 2.0
**Status:** Implemented
**Semantic View:** `CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS`

## 1. Purpose

This document defines the business meaning, calculation logic, grain and interpretation of ChainLoom's 12 governed metrics as implemented in the semantic view.

## 2. Metric Design Principles

1. One canonical definition per metric.
2. Explicit eligibility criteria.
3. Explicit grain.
4. No accidental double counting.
5. Explainable calculation.
6. Evidence-backed results.
7. AI does not invent formulas.
8. Missing values are preserved as NULL, never silently converted to zero.

## 3. Metric Catalogue

### Customer Fulfillment Surface

| # | Metric | Expression |
|---|--------|------------|
| M01 | Fulfillment Rate | `SUM(FULFILLED_QUANTITY) / NULLIF(SUM(ORDERED_QUANTITY), 0)` |
| M02 | Order Lines with Fulfillment Gaps | `COUNT_IF(FULFILLMENT_GAP_FLAG = TRUE)` |

### Shipment Performance Surface

| # | Metric | Expression |
|---|--------|------------|
| M03 | On-Time Delivery Rate | `COUNT_IF(ON_TIME_FLAG = TRUE) / NULLIF(COUNT_IF(DELIVERY_ELIGIBLE_FLAG = TRUE), 0)` |
| M04 | Avg Delivery Delay Days | `AVG(CASE WHEN DELIVERY_ELIGIBLE_FLAG = TRUE THEN DELIVERY_DELAY_DAYS END)` |

### Production Performance Surface

| # | Metric | Expression |
|---|--------|------------|
| M05 | Production Attainment | `SUM(PRODUCED_QUANTITY) / NULLIF(SUM(PLANNED_QUANTITY), 0)` |
| M06 | Constrained Production Days | `COUNT_IF(CONSTRAINT_FLAG = TRUE)` |
| M07 | P104 Exposed Production Days | `COUNT_IF(P104_EXPOSURE_FLAG = TRUE)` |

### Inventory Position Surface

| # | Metric | Expression | Semi-Additive |
|---|--------|------------|---------------|
| M08 | Total On Hand | `SUM(ON_HAND_QUANTITY)` | Yes — by SNAPSHOT_DATE |
| M09 | Total Available | `SUM(AVAILABLE_QUANTITY)` | Yes — by SNAPSHOT_DATE |
| M10 | Parts Below Safety Stock | `COUNT_IF(BELOW_SAFETY_STOCK_FLAG = TRUE)` | Yes — by SNAPSHOT_DATE |

### Supplier Performance Surface

| # | Metric | Expression |
|---|--------|------------|
| M11 | Defect Rate | `SUM(DEFECTIVE_QUANTITY) / NULLIF(SUM(INSPECTED_QUANTITY), 0)` |
| M12 | Rejection Rate | `SUM(REJECTED_QUANTITY) / NULLIF(SUM(RECEIVED_QUANTITY), 0)` |

## 4. Metric Details

### M01 — Fulfillment Rate

**Surface:** CUSTOMER_FULFILLMENT

**Grain:** Order Line.

Ratio of fulfilled to ordered quantity. Returns NULL when ordered quantity is zero.

### M02 — Order Lines with Fulfillment Gaps

**Surface:** CUSTOMER_FULFILLMENT

**Grain:** Order Line.

Count of order lines where unfulfilled quantity exists (FULFILLMENT_GAP_FLAG = TRUE).

### M03 — On-Time Delivery Rate

**Surface:** SHIPMENT_PERFORMANCE

**Grain:** Shipment.

Ratio of on-time eligible shipments to all eligible delivered shipments. Eligible means DELIVERY_ELIGIBLE_FLAG = TRUE (promised and actual delivery dates exist, shipment is not cancelled). On-time means ON_TIME_FLAG = TRUE (actual delivery on or before promised date).

Never include in-transit or cancelled shipments in the denominator.

### M04 — Avg Delivery Delay Days

**Surface:** SHIPMENT_PERFORMANCE

**Grain:** Shipment (eligible delivered only).

Average DELIVERY_DELAY_DAYS for eligible delivered shipments. Non-eligible shipments are excluded via CASE expression.

### M05 — Production Attainment

**Surface:** PRODUCTION_PERFORMANCE

**Grain:** Plant × Product × Production Date.

Ratio of actual to planned production. Returns NULL when planned quantity is zero.

### M06 — Constrained Production Days

**Surface:** PRODUCTION_PERFORMANCE

**Grain:** Plant × Product × Production Date.

Count of production-days where CONSTRAINT_FLAG = TRUE.

### M07 — P104 Exposed Production Days

**Surface:** PRODUCTION_PERFORMANCE

**Grain:** Plant × Product × Production Date.

Count of production-days where the product's BOM includes Part P104. This indicates BOM dependency only — it does NOT prove P104 caused any production disruption.

### M08 — Total On Hand

**Surface:** INVENTORY_POSITION

**Grain:** Part × Plant × Snapshot Date.

Sum of on-hand quantity. **Semi-additive by SNAPSHOT_DATE:** can be summed across parts and plants for a single date, but must NOT be summed across dates.

### M09 — Total Available

**Surface:** INVENTORY_POSITION

**Grain:** Part × Plant × Snapshot Date.

Sum of available quantity (on-hand minus reserved). **Semi-additive by SNAPSHOT_DATE.**

### M10 — Parts Below Safety Stock

**Surface:** INVENTORY_POSITION

**Grain:** Part × Plant × Snapshot Date.

Count of part-plant combinations where available quantity is below safety stock. **Semi-additive by SNAPSHOT_DATE.** For current status, filter to the latest snapshot date.

### M11 — Defect Rate

**Surface:** SUPPLIER_PERFORMANCE

**Grain:** Supplier × Part (pre-aggregated).

Weighted defect rate computed from additive counts (defective quantity / inspected quantity). This is the governed aggregate metric — do NOT average the pre-computed per-row DEFECT_RATE_PCT column across rows.

### M12 — Rejection Rate

**Surface:** SUPPLIER_PERFORMANCE

**Grain:** Supplier × Part (pre-aggregated).

Weighted rejection rate computed from additive counts (rejected quantity / received quantity). Same aggregation rule as Defect Rate.

## 5. Pre-Aggregated Supplier Ratios

The SUPPLIER_PERFORMANCE surface includes three pre-computed per-row ratio columns:

- AVG_RECEIPT_DELAY_DAYS
- ON_TIME_RECEIPT_PCT
- DEFECT_RATE_PCT

These are **non-additive.** Do not SUM or AVG them across rows. For aggregate supplier analysis, use the governed metrics M11 (Defect Rate) and M12 (Rejection Rate), which recompute from additive base quantities.

## 6. Supplier Attribution Rules

Capability: Supplier → Supplier-Part → Part

Commitment: Supplier → PO Line → Part → Plant

Actual supply: Supplier → Supply Receipt → Part → Plant

Capability is not actual supply. Actual supply is not proof of exact downstream causality without lot/batch genealogy.

## 7. Inventory Rules

- Never sum daily inventory snapshots to answer a point-in-time inventory question.
- The semantic layer treats inventory metrics as semi-additive across time via `NON ADDITIVE BY`.
- Current inventory requires filtering to the latest snapshot date.

## 8. Metric Anti-Patterns

Avoid:
- Fact-to-fact fan-out (joining CUSTOMER_FULFILLMENT to SHIPMENT_PERFORMANCE, etc.)
- Undefined denominators
- Hidden filters
- Multiple definitions for one metric
- AI-invented formulas
- Ambiguous supplier attribution
- Unsupported causal claims
- Summing inventory across snapshot dates
- Averaging pre-aggregated non-additive ratios

## 9. Product Risk Signals

V_PRODUCT_RISK_SIGNALS exposes product-level rates (FULFILLMENT_RATE, ON_TIME_DELIVERY_RATE, PRODUCTION_ATTAINMENT) as facts, and three risk flags plus RISK_SIGNAL_COUNT as dimensions. These are independently observed indicators from separate analytical surfaces.

RISK_SIGNAL_COUNT is a simple co-occurrence count (0–3). Co-occurrence is observational only and does NOT imply causality between fulfillment gaps, delivery delays, and production constraints.
