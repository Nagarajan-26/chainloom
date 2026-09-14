# ChainLoom

> Governed supply-chain intelligence built on Snowflake.

**Problem Statement:** Supply Chain Ontology and Governed Conversational Analytics

---

## What ChainLoom Does

ChainLoom is a Snowflake-native supply-chain Control Tower that connects fragmented supply-chain data through a governed semantic layer, enabling natural-language analytics with explicit analytical boundaries.

Users can ask questions like:

- *Which products currently show multiple risk signals?*
- *What is the on-time delivery rate by carrier?*
- *Which parts are below safety stock?*

ChainLoom answers from governed definitions, shows supporting SQL and data, and explicitly states what the model can and cannot establish.

## Why It Matters

Supply-chain data is scattered across ERP, logistics, supplier and operational systems. The same question produces different answers depending on which team runs it. ChainLoom solves this with:

- **One governed semantic layer** — a single authoritative source for metric definitions, entity relationships and analytical boundaries.
- **Explicit analytical boundaries** — fact-to-fact joins are blocked, causal inference is prohibited where lot/batch genealogy is unavailable, and inventory is snapshot-aware.
- **Independent risk signals** — product-level risk is reported as co-occurrence of independently observed threshold breaches, never as a composite score or causal chain.

## Architecture

```text
RAW (16 tables)
  → CURATED (6 analytical views)
    → SEMANTIC VIEW (11 logical tables, 12 governed metrics, 14 relationships)
      → Cortex Analyst REST API
        → Streamlit Control Tower
```

**Database:** `CHAINLOOM` with schemas `RAW`, `CURATED`, `SEMANTIC`.

**Semantic View:** `CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS`

**Curated Analytical Surfaces:**

| Surface | Grain |
|---------|-------|
| V_SUPPLIER_PERFORMANCE | Supplier × Part |
| V_INVENTORY_POSITION | Part × Plant × Snapshot Date |
| V_PRODUCTION_PERFORMANCE | Plant × Product × Production Date |
| V_CUSTOMER_FULFILLMENT | Order Line |
| V_SHIPMENT_PERFORMANCE | Shipment |
| V_PRODUCT_RISK_SIGNALS | Product |

Each surface is independently queryable. Fact-to-fact joins are intentionally not modeled to prevent fan-out and cross-grain aggregation errors.

**Verified Queries:** Q1–Q10 (operational), Q13 (product risk signals). Q11–Q12 are governance boundary checks (causal and attribution boundaries).

## Deployment

The Streamlit application runs on Snowflake Container Runtime. It authenticates via OAuth session token and calls the Cortex Analyst REST API against the semantic view.

**Entry point:** `streamlit/Home.py`

**Deployment path:** GitHub → Snowflake Git Repository → Snowflake Container Runtime

## Core Scenario

A controlled synthetic disruption demonstrates governed multi-surface analysis:

```text
Supplier S017 delays → Part P104 availability → PL03 inventory pressure
→ Production constraints → Order exposure → Shipment delays → Customer impact
```

The scenario is deterministic so results can be independently verified.

## Repository Structure

```text
chainloom/
├── AGENTS.md                          AI agent instructions
├── README.md                          This file
├── docs/
│   ├── ARCHITECTURE.md                System architecture
│   ├── METRICS.md                     Governed metric definitions
│   ├── ONTOLOGY.md                    Supply-chain ontology
│   ├── PROJECT_CHARTER.md             Project charter and scope
│   └── demo/
│       ├── DEMO_SCRIPT.md             Judge-facing demo script
│       └── QUESTION_CATALOG.md        Verified question catalog
├── sql/
│   ├── 01_foundation/                 Database and schema DDL
│   ├── 02_raw/                        Table DDL, seed data, validation
│   ├── 03_curated/                    Curated view DDL, validation
│   └── 04_semantic/                   Semantic view DDL, validation
└── streamlit/
    └── Home.py                        Streamlit Control Tower application
```

## Governance Approach

1. **No unsupported fact-to-fact joins.** Each analytical surface is queried independently.
2. **Inventory is semi-additive.** Snapshot quantities must not be summed across dates.
3. **No causal inference.** Supplier-to-customer causality cannot be established without lot/batch genealogy.
4. **Missing values are preserved.** Unavailable metrics display as "—", never silently converted to zero.
5. **Risk signals are independent observations.** RISK_SIGNAL_COUNT counts threshold breaches; it is not a weighted or composite score.
6. **AI does not invent formulas.** All metric definitions originate from the governed semantic layer.

## Development Principles

- Correctness over feature count.
- Current Snowflake GA capabilities.
- Explicit business definitions and grain.
- Deterministic synthetic scenarios.
- Evidence over unsupported AI claims.
