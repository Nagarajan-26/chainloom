# ChainLoom — Question Catalog

**Version:** 2.0
**Semantic View:** `CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS`

## Operational Verified Queries (Q1–Q10)

These are embedded in the semantic view as verified queries to ground Cortex Analyst.

| ID | Surface | Question |
|----|---------|----------|
| Q1 | Customer Fulfillment | What is the fulfillment rate by customer segment? |
| Q2 | Customer Fulfillment | Which product families have the most order lines with fulfillment gaps? |
| Q3 | Shipment Performance | What is the on-time delivery rate for each carrier? |
| Q4 | Shipment Performance | What is the average delivery delay in days for each customer priority tier? |
| Q5 | Production Performance | What is the production attainment rate for each plant? |
| Q6 | Production Performance | How many constrained production days occurred for products that depend on Part P104? |
| Q7 | Inventory Position | How many parts are currently below safety stock at each plant? |
| Q8 | Inventory Position | Show the total available inventory quantity for each snapshot date. |
| Q9 | Supplier Performance | What is the defect rate for each supplier tier? |
| Q10 | Supplier Performance | Which suppliers have an average receipt delay greater than 2 days? |

## Product Risk Signal Query (Q13)

| ID | Surface | Question |
|----|---------|----------|
| Q13 | Product Risk Signals | Which products currently show multiple independent supply-chain risk signals across fulfillment, delivery, and production? |

Q13 queries V_PRODUCT_RISK_SIGNALS, which synthesizes independent threshold breaches from three analytical surfaces. RISK_SIGNAL_COUNT is a co-occurrence count (0–3), not a weighted or composite risk score.

## Governance Boundary Checks (Q11–Q12)

These are not embedded as verified queries. They are tested through the Trust & Governance section of the application to demonstrate that the model correctly refuses unsupported causal claims.

| ID | Boundary | Question |
|----|----------|----------|
| Q11 | Causal Boundary | Did Part P104 inventory shortages cause production constraints last month? |
| Q12 | Attribution Boundary | Which supplier delivery delays directly caused late shipments to our Strategic customers? |

**Q11 — Causal Boundary:** The model can independently report BOM exposure and production constraints, but cannot establish that inventory shortages caused production constraints because the inventory and production surfaces are not joined.

**Q12 — Attribution Boundary:** The model can independently observe supplier delays and shipment delays, but cannot establish direct supplier-to-customer causation because lot/batch genealogy is unavailable.

## Additional Demonstration Questions

These are available through the Ask ChainLoom console and leverage the governed semantic model:

- Which products currently show multiple risk signals?
- Which carriers have the lowest on-time delivery?
- Which parts are below safety stock?
- Which suppliers have the highest defect rate?
