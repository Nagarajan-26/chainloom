# ChainLoom — System Architecture

**Version:** 2.0
**Status:** Implemented and Deployed
**Problem Statement:** Supply Chain Ontology and Governed Conversational Analytics

## 1. Architecture Objective

ChainLoom is a Snowflake-native governed supply-chain intelligence application. It provides governed conversational analytics over a shared ontology with consistent metric definitions, explicit analytical boundaries, and evidence-backed answers.

## 2. Architecture Principles

1. Snowflake is the system of record.
2. The Semantic View is the governed business contract.
3. Physical data and semantic data are separate layers.
4. Every fact has explicit grain.
5. AI does not invent business definitions.
6. Unsupported causal claims are prohibited.
7. Missing values are preserved, never silently converted.

## 3. High-Level Architecture

```text
                         ┌──────────────────────┐
                         │        USER           │
                         │ Natural-language       │
                         │ supply-chain query     │
                         └──────────┬────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  STREAMLIT            │
                         │  Control Tower        │
                         │  (Home.py)            │
                         └──────────┬────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  CORTEX ANALYST       │
                         │  REST API             │
                         └──────────┬────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  SEMANTIC VIEW        │
                         │  CHAINLOOM_ANALYTICS  │
                         └──────────┬────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  CURATED LAYER        │
                         │  6 analytical views   │
                         └──────────┬────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  RAW LAYER            │
                         │  16 physical tables   │
                         └──────────────────────┘
```

## 4. Data Layering

```text
RAW  →  CURATED  →  SEMANTIC  →  Cortex Analyst  →  Streamlit
```

### RAW Schema

16 physical tables in `CHAINLOOM.RAW`:

**Dimensions:** DATE_DIM, SUPPLIER, PART, PRODUCT, PLANT, CUSTOMER, CARRIER

**Bridges:** SUPPLIER_PART, PRODUCT_PART

**Facts:** PURCHASE_ORDER_LINE, SUPPLY_RECEIPT, INVENTORY, PRODUCTION, QUALITY, ORDER_LINE, SHIPMENT

### CURATED Schema

6 analytical views in `CHAINLOOM.CURATED`:

| View | Grain | Purpose |
|------|-------|---------|
| V_SUPPLIER_PERFORMANCE | Supplier × Part | Pre-aggregated supplier scorecard |
| V_INVENTORY_POSITION | Part × Plant × Snapshot Date | Snapshot-aware inventory position |
| V_PRODUCTION_PERFORMANCE | Plant × Product × Production Date | Production output with BOM exposure |
| V_CUSTOMER_FULFILLMENT | Order Line | Demand fulfillment tracking |
| V_SHIPMENT_PERFORMANCE | Shipment | Delivery performance and delay analysis |
| V_PRODUCT_RISK_SIGNALS | Product | Multi-surface risk signal summary |

Each curated view joins RAW facts with RAW dimensions to produce a self-contained analytical surface. V_PRODUCT_RISK_SIGNALS is a second-level curated view that aggregates from V_CUSTOMER_FULFILLMENT, V_SHIPMENT_PERFORMANCE, and V_PRODUCTION_PERFORMANCE.

### SEMANTIC Schema

One semantic view: `CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS`

- 11 logical tables (6 curated surfaces + 5 RAW dimensions)
- 14 relationships (fact-to-dimension only)
- 12 governed metrics
- 11 verified queries (Q1–Q10, Q13)
- Extensive `ai_sql_generation` instructions

## 5. Independent Analytical Surfaces

Each curated view represents an independent analytical surface with its own grain and metrics. The semantic view models these as separate fact tables with shared conformed dimensions (Date, Plant, Product, Part, Carrier).

**Fact-to-fact joins are intentionally not modeled.** This prevents:
- Fan-out from mismatched grains
- Cross-grain aggregation errors
- Unsupported causal inference between surfaces

Cross-surface analysis is handled by V_PRODUCT_RISK_SIGNALS, which aggregates each surface independently at the product level before combining results.

## 6. Product Risk Signal Synthesis

V_PRODUCT_RISK_SIGNALS computes three independent risk flags per product:

| Flag | Source Surface | Threshold |
|------|---------------|-----------|
| FULFILLMENT_RISK_FLAG | V_CUSTOMER_FULFILLMENT | Fulfillment rate < 90% |
| DELIVERY_RISK_FLAG | V_SHIPMENT_PERFORMANCE | On-time delivery rate < 85% |
| PRODUCTION_RISK_FLAG | V_PRODUCTION_PERFORMANCE | Production attainment < 90% |

RISK_SIGNAL_COUNT (0–3) counts how many flags are TRUE. This is a simple co-occurrence count. It does not imply that one signal caused another, and it is not a weighted or composite risk score.

## 7. Inventory Snapshot Grain

Inventory is a periodic snapshot at the Part × Plant × Snapshot Date grain.

- Quantities can be summed across parts and plants for a single snapshot date.
- Quantities must NOT be summed across multiple snapshot dates.
- Current inventory uses `WHERE SNAPSHOT_DATE = (SELECT MAX(SNAPSHOT_DATE) ...)`.
- The semantic view declares inventory metrics as `NON ADDITIVE BY (SNAPSHOT_DATE ASC NULLS LAST)`.

## 8. Causal and Attribution Boundary

ChainLoom does not implement lot/batch genealogy. Therefore:

- **Cannot claim:** Receipt R123 caused Shipment S456 to be late.
- **Can claim:** Supplier S017 has elevated receipt delays, and shipment delays are independently observed for products that depend on parts supplied by S017.

The application explicitly communicates what the data can and cannot establish through governance boundary checks in the Trust & Governance section of the UI.

## 9. Cortex Analyst Integration

The Streamlit application calls the Cortex Analyst REST API:

```text
POST https://{SNOWFLAKE_HOST}/api/v2/cortex/analyst/message
Authorization: Bearer {Container Runtime OAuth token}
Body: { messages: [...], semantic_view: "CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS" }
```

Cortex Analyst generates SQL grounded in the semantic view's definitions, relationships, metrics, verified queries, and `ai_sql_generation` instructions. The application executes the generated SQL and presents results with governance metadata.

## 10. Application Architecture

The application is a single-file Streamlit application (`streamlit/Home.py`) deployed on Snowflake Container Runtime.

**UI sections:**
1. Executive KPI strip (Fulfillment Rate, OTD Rate, risk counts)
2. Priority Attention (highest-signal product with governed explanation)
3. Network Posture (product risk distribution)
4. Network Inventory Intelligence (snapshot-aware trend chart with safety stock)
5. Product Risk Intelligence (full product risk table)
6. Ask ChainLoom (Cortex Analyst investigation console)
7. Trust & Governance (posture overview, boundary checks, governance controls)

**Data flow:**
- Dashboard panels query curated views directly via Snowpark session
- Investigation console sends questions to Cortex Analyst REST API
- Results display with finding, data table, generated SQL, and governance metadata

## 11. Deployment Architecture

```text
Developer workstation
  → Git push
    → GitHub repository
      → Snowflake Git Repository integration
        → Snowflake Container Runtime
          → Streamlit application (Home.py)
```

The application authenticates via the Container Runtime OAuth session token at `/snowflake/session/token`. No credentials are embedded in the application code.

## 12. Semantic View Relationship Map

```text
DATE_DIM ←── CUSTOMER_FULFILLMENT ──→ PLANT
                                   ──→ PRODUCT

DATE_DIM ←── SHIPMENT_PERFORMANCE ──→ PLANT
                                   ──→ PRODUCT
                                   ──→ CARRIER

DATE_DIM ←── PRODUCTION_PERFORMANCE ──→ PLANT
                                     ──→ PRODUCT

DATE_DIM ←── INVENTORY_POSITION ──→ PLANT
                                 ──→ PART

         SUPPLIER_PERFORMANCE ──→ PART
```

14 relationships, all fact-to-dimension. No fact-to-fact relationships.

## 13. Verified Query Strategy

11 verified queries embedded in the semantic view:

| ID | Surface | Question |
|----|---------|----------|
| Q1 | Customer Fulfillment | Fulfillment rate by customer segment |
| Q2 | Customer Fulfillment | Product families with most fulfillment gaps |
| Q3 | Shipment Performance | On-time delivery rate by carrier |
| Q4 | Shipment Performance | Average delivery delay by customer priority |
| Q5 | Production Performance | Production attainment by plant |
| Q6 | Production Performance | Constrained days for P104-dependent products |
| Q7 | Inventory Position | Parts below safety stock at each plant (current) |
| Q8 | Inventory Position | Available inventory trend by snapshot date |
| Q9 | Supplier Performance | Defect rate by supplier tier |
| Q10 | Supplier Performance | Suppliers with high receipt delay |
| Q13 | Product Risk Signals | Products with multiple independent risk signals |

Q11 and Q12 are governance boundary checks tested through the Trust & Governance UI section, not embedded as verified queries.

## 14. Security

- No credentials in application code or repository.
- Container Runtime OAuth authentication.
- Synthetic data only — no real personal or confidential information.

## 15. Cost Controls

- Small development warehouse with auto-suspend.
- Controlled synthetic-data volume (92 days, manageable row counts).
- Cached application results (`@st.cache_data(ttl=120)`).
- Single Cortex Analyst call per user question.

## 16. Architecture Boundaries

ChainLoom does not include:
- External ERP integration
- Real production data
- Lot/batch genealogy
- Autonomous procurement or order modification
- Production-scale streaming
- ML forecasting
- Warehouse/bin-level inventory
- Cortex Agent orchestration (investigation is handled through Cortex Analyst)

## 17. Repository Structure

```text
chainloom/
├── AGENTS.md                                   AI agent instructions
├── README.md                                   Project README
├── docs/                                       Design documentation
├── sql/
│   ├── 01_foundation/                          Database and schema DDL
│   ├── 02_raw/                                 Table DDL, seed data, validation
│   ├── 03_curated/                             Curated view DDL, validation
│   └── 04_semantic/                            Semantic view DDL, validation
└── streamlit/
    └── Home.py                                 Streamlit Control Tower
```

## 18. Architecture Principle

```text
                     BUSINESS QUESTION
                            │
                            ▼
               STREAMLIT CONTROL TOWER
                   (Ask ChainLoom)
                            │
                            ▼
                     CORTEX ANALYST
                            │
                            ▼
                GOVERNED SEMANTIC VIEW
                 (CHAINLOOM_ANALYTICS)
                            │
                            ▼
              CURATED ANALYTICAL SURFACES
                            │
                            ▼
                     RAW DATA LAYER
                            │
                            ▼
                   EVIDENCE + RESULT
```

The architecture preserves the chain:

**Business question → Control Tower → Cortex Analyst → governed semantics → curated data → raw data → evidence → decision support.**
