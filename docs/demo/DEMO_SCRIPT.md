# ChainLoom — Demo Script

**Audience:** Hackathon judges
**Duration:** 4–6 minutes
**Theme:** Governed conversational analytics with explicit analytical boundaries

---

## Opening (30 seconds)

ChainLoom is a Snowflake-native supply-chain Control Tower. It connects fragmented supply-chain data through a governed semantic layer so natural-language questions return consistent, trustworthy answers — and explicitly states what the model can and cannot establish.

---

## Step 1 — What needs attention? (45 seconds)

**Show:** The Control Tower dashboard as it loads.

Point out the executive KPI strip (Fulfillment Rate, On-Time Delivery, risk counts), the Priority Attention card showing the highest-signal product, and the Network Posture breakdown.

**Key point:** These are live governed metrics from independent analytical surfaces, not hardcoded values.

---

## Step 2 — Investigate supply-chain risk (60 seconds)

**Ask ChainLoom:** *Which products currently show multiple risk signals?*

This triggers Cortex Analyst against the governed semantic view. Show the result table from V_PRODUCT_RISK_SIGNALS.

**Key point:** Each risk flag (fulfillment, delivery, production) is independently computed from its own analytical surface. RISK_SIGNAL_COUNT counts co-occurrences — it is not a composite score and does not imply causality.

---

## Step 3 — Drill into a specific signal (60 seconds)

**Ask ChainLoom:** *Which carriers have the lowest on-time delivery rate?*

Show the generated SQL and results. Point out that the query uses only the SHIPMENT_PERFORMANCE surface with governed metric definitions.

Then ask: *Which parts are currently below safety stock?*

**Key point:** Inventory results are snapshot-aware — the query filters to the latest snapshot date. Quantities are never summed across dates.

---

## Step 4 — Evidence and provenance (45 seconds)

Expand the governance metadata on a result:
- Semantic View name
- Request ID
- Generated SQL visible in the "View generated SQL" expander

**Key point:** Every answer traces back to the governed semantic layer. The application does not fabricate evidence.

---

## Step 5 — Test the boundaries (90 seconds)

Navigate to the **Trust & Governance** section. Show the live governance posture:
- Semantic Layer: CONNECTED
- Verified Queries: 11
- Fact-to-Fact Joins: BLOCKED
- Causal Inference: BLOCKED
- Inventory Grain: SNAPSHOT
- Missing Values: PRESERVED

**Test Boundary 1 — Causal Boundary:**

Click "Test Boundary" on: *Did Part P104 inventory shortages cause production constraints last month?*

Show the result with the explicit governance interpretation:
- **Can establish:** BOM exposure and production constraints can be independently reported.
- **Cannot establish:** Causation cannot be established without a valid linkage between the inventory and production surfaces.

**Test Boundary 2 — Attribution Boundary:**

Click "Test Boundary" on: *Which supplier delivery delays directly caused late shipments to our Strategic customers?*

- **Can establish:** Supplier and shipment delays can be independently observed.
- **Cannot establish:** Direct supplier-to-customer causation cannot be established because lot/batch genealogy is unavailable.

**Key point:** ChainLoom explicitly refuses unsupported causal claims rather than generating a plausible-sounding but unfounded narrative. This is the core differentiator.

---

## Closing (30 seconds)

ChainLoom demonstrates that governed conversational analytics is not just about answering questions — it is about knowing what the data can and cannot establish, and communicating that clearly.

Built entirely on Snowflake: Semantic Views, Cortex Analyst, Container Runtime. No external infrastructure.
