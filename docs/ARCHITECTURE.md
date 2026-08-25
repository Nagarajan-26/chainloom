# ChainLoom — System Architecture

**Status:** Architecture Approved / Model Hardened
**Version:** 1.1
**Problem Statement:** Supply Chain Ontology and Governed Conversational Analytics
**Architecture Target:** Snowflake 2026 platform

## 1. Architecture Objective

ChainLoom is a Snowflake-native governed supply-chain intelligence application providing governed analytics, a shared ontology, consistent metrics, investigation, impact analysis, evidence and evaluation.

## 2. Architecture Principles

1. Snowflake is the system of record.
2. The Semantic View is the governed business contract.
3. Physical data and semantic data are separate layers.
4. Every fact has explicit grain.
5. AI does not invent business definitions.
6. Investigation is evidence-driven.
7. Unsupported causal claims are prohibited.

## 3. High-Level Architecture

```text
                         ┌──────────────────────┐
                         │        USER          │
                         │ Natural-language     │
                         │ supply-chain query   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │  CHAINLOOM APP       │
                         │  Streamlit            │
                         └──────────┬───────────┘
                                    │
                  ┌─────────────────┴─────────────────┐
                  │                                   │
                  ▼                                   ▼
        ┌─────────────────────┐            ┌─────────────────────┐
        │ GOVERNED ANALYTICS  │            │ INVESTIGATION       │
        │ Cortex Analyst      │            │ Cortex Agent        │
        └──────────┬──────────┘            └──────────┬──────────┘
                   │                                  │
                   └────────────────┬─────────────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ GOVERNED SEMANTIC    │
                         │ VIEW                 │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ CURATED DATA LAYER   │
                         └──────────┬───────────┘
                                    │
                                    ▼
                         ┌──────────────────────┐
                         │ SYNTHETIC SUPPLY     │
                         │ CHAIN DATA           │
                         └──────────────────────┘
```

## 4. User Interaction Modes

### Governed Analytics
Direct metric, filtering, comparison and dimensional questions.

### Investigation
Multi-step questions requiring relationship traversal, impact analysis and evidence assembly.

## 5. Cortex Analyst Role

Cortex Analyst handles governed structured-data analytics over the ChainLoom Semantic View.

The Semantic View remains authoritative for metric definitions, relationships and business terminology.

## 6. Cortex Agent Role

Cortex Agent is the orchestration layer for complex multi-step workflows.

```text
User question
→ Identify intent
→ Identify business concepts
→ Query governed data
→ Evaluate intermediate results
→ Perform additional analysis
→ Trace relationships
→ Assemble evidence
→ Grounded response
```

## 7. Current Semantic View Design Requirements

Current Snowflake Semantic Views support explicit relationships, bridge-table modeling for many-to-many concepts, role-playing logical tables, semi-additive metrics through `NON ADDITIVE BY`, derived metrics, and relationship selection for metrics when multiple paths exist. Relationship-path selection is currently Preview.

Verified queries can be embedded in semantic views to improve Cortex Analyst accuracy and trustworthiness.

ChainLoom will:
- Define only relationships required by supported question patterns.
- Use bridge tables for many-to-many concepts.
- Treat inventory as semi-additive.
- Use explicit metric relationship paths where appropriate.
- Add verified queries after the semantic model is stable.

## 8. Physical Data Architecture

### Dimensions

```text
DIM_DATE
DIM_SUPPLIER
DIM_PART
DIM_PRODUCT
DIM_PLANT
DIM_CUSTOMER
DIM_CARRIER
```

### Bridges

```text
BRIDGE_SUPPLIER_PART
BRIDGE_PRODUCT_PART
```

### Procurement / supply

```text
FACT_PURCHASE_ORDER_LINE
FACT_SUPPLY_RECEIPT
```

### Manufacturing

```text
FACT_INVENTORY
FACT_PRODUCTION
FACT_QUALITY
```

### Demand / fulfillment

```text
FACT_ORDER_LINE
FACT_SHIPMENT
```

**Total: 16 physical tables.**

## 9. Fact Grain Contract

```text
FACT_PURCHASE_ORDER_LINE
= one row per PO line

FACT_SUPPLY_RECEIPT
= one row per receipt event / receipt line

FACT_INVENTORY
= one row per Part × Plant × Snapshot Date

FACT_PRODUCTION
= one row per Plant × Product × Production Date

FACT_ORDER_LINE
= one row per customer order line

FACT_SHIPMENT
= one row per shipment event

FACT_QUALITY
= one row per Supplier × Part × Plant inspection event
```

These grains are part of the ChainLoom data contract.

## 10. Data Layering

```text
SOURCE / SYNTHETIC
        ↓
RAW
        ↓
CURATED
        ↓
SEMANTIC
        ↓
AI / APPLICATION
```

## 11. Proposed Database Structure

```text
CHAINLOOM
│
├── RAW
├── CURATED
├── SEMANTIC
├── ANALYTICS
└── APP
```

Only schemas needed by the current phase will be created.

## 12. Semantic View Boundary

Initial business concepts:
- Supplier
- Part
- Product
- Plant
- Inventory
- Purchase Order Line
- Supply Receipt
- Customer
- Order
- Shipment
- Carrier

Governed metrics:
- On-Time Delivery Rate
- Late Shipment Count
- Fill Rate
- Average Supplier Lead Time
- Supplier Inbound On-Time Rate
- Supplier Defect Rate
- Inventory Coverage Days
- At-Risk Order Count
- At-Risk Shipment Count
- Confirmed Impacted Customer Count
- At-Risk Customer Count

## 13. Relationship Strategy

```text
Supplier → Purchase Order Line
Supplier → Supply Receipt
Supplier → Supplier-Part
Purchase Order Line → Supply Receipt
Part → Supply Receipt
Part → Product-Part
Product → Product-Part
Product → Production
Product → Order Line
Plant → Purchase Order Line
Plant → Supply Receipt
Plant → Inventory
Plant → Production
Plant → Order Line
Plant → Quality
Customer → Order Line
Order Line → Shipment
Carrier → Shipment
```

The semantic layer must not expose unrestricted fact-to-fact traversal as a universal join graph.

## 14. Supplier Attribution

Capability:
Supplier → Supplier-Part → Part

Commitment:
Supplier → PO Line → Part → Plant

Actual supply:
Supplier → Supply Receipt → Part → Plant

Downstream operational dependency:
Supplier → Supply / Inventory → Product → Order → Shipment → Customer

The MVP has no lot-level genealogy and therefore does not claim exact receipt-to-shipment causality.

## 15. Metric Computation Architecture

```text
SHIPMENT
   ↓
Shipment-grain aggregation
   ↓
OTD / Late Shipment Count
```

```text
PO LINE + SUPPLY RECEIPT
   ↓
Commitment vs actual receipt
   ↓
Supplier Inbound OTD / Realized Lead Time
```

```text
INVENTORY + DEMAND
   ↓
Part × Plant × Date
   ↓
Inventory Coverage Days
```

```text
ORDER LINE
   ↓
Order-line aggregation
   ↓
Fill Rate / At-Risk Orders
```

Raw fact-to-fact joins require controlled grain.

## 16. Inventory Semantics

Inventory is a periodic snapshot and is semi-additive across time.

Current/latest inventory must select the appropriate latest snapshot at the requested Part × Plant grain.

The Semantic View should use `NON ADDITIVE BY` where required to preserve this behavior.

## 17. Investigation Architecture

Example:

```text
Why did OTD decline?
→ current OTD
→ comparison OTD
→ deterioration by dimension
→ strongest contributor
→ relationship trace
→ quantified findings
→ evidence-backed explanation
```

## 18. Impact Analysis

### Confirmed impact
Observed delayed shipment linked to a customer.

### Potential risk
Deterministic risk condition:

```text
Open Order
+
Supply dependency
+
Insufficient inventory coverage
+
Promised-date exposure
```

These populations remain separate.

## 19. Impact Explorer

Example:

```text
Supplier S017
      │
      ├── PO / Supply Receipt
      ├── Part P104
      │       │
      │       └── Plant PL03
      │               ├── Inventory ↓
      │               ├── Production ↓
      │               └── Orders exposed
      │
      └── Other supplied parts
```

## 20. Evidence Architecture

```text
Answer
  ↓
Metric / Business Definition
  ↓
Semantic Concept
  ↓
Verified Query where applicable
  ↓
Generated SQL
  ↓
Supporting Result
```

## 21. Verified Query Strategy

Maintain a Golden Question Set covering basic metrics, dimensional analytics, relationships, multi-hop analysis, investigation, impact and unsupported/boundary questions.

Add verified queries after tables, columns, descriptions and metrics are stable.

## 22. Cortex Analyst Evaluation

Measure:
- SQL correctness
- Result correctness
- Semantic interpretation
- Regression
- Latency

Start with approximately 10 representative benchmark questions and expand based on failures.

## 23. Application Architecture

```text
app/
├── streamlit_app.py
├── ui/
│   ├── chat.py
│   ├── metrics.py
│   ├── investigation.py
│   ├── impact.py
│   └── evidence.py
├── services/
│   ├── agent.py
│   ├── analytics.py
│   └── evidence.py
└── config/
    └── settings.py
```

## 24. Streamlit Deployment

Preferred target: Streamlit in Snowflake.

Use the runtime supported by the hackathon account and current Snowflake capabilities. Avoid unnecessary infrastructure.

## 25. Git and Development Architecture

```text
Local VS Code
      ↓
Git
      ↓
GitHub
      ↓
Snowflake deployment
      ↓
Validation
```

Codex is primarily for repository/software engineering. Snowflake-native AI assistance is for Snowflake-specific development and exploration.

## 26. Security

Never commit passwords, tokens, private keys, API secrets or connection credentials.

Synthetic data contains no real personal or confidential information.

## 27. Cost Architecture

Controls:
- Small development warehouse
- Auto-suspend
- Controlled synthetic-data volume
- Avoid repeated full-table scans
- Cache application results where appropriate
- Avoid unnecessary agent calls
- Monitor credit usage

## 28. Failure Handling

Unsupported questions → explain model limitations.

Ambiguous questions → request clarification.

Query failure → show useful error state; never fabricate.

Missing evidence → do not claim unsupported confidence.

Agent failure → use a simpler governed path where possible.

## 29. Observability

Retain enough information to debug:
- User question
- Workflow
- Semantic concept
- Generated SQL
- Query ID where available
- Execution result
- Response status
- Evaluation outcome

Do not log secrets.

## 30. Architecture Boundaries

Initial ChainLoom does not include:
- External ERP integration
- Real production data
- Lot/batch genealogy
- Autonomous procurement
- Autonomous order modification
- Production-scale streaming
- Full ML forecasting platform
- Warehouse/bin-level inventory management
- Microservice infrastructure

## 31. Implementation Sequence

### Phase 1 — Snowflake foundation
Database → Schemas → Warehouse → Validation

### Phase 2 — Physical model
Tables → keys → relationships → grain validation

### Phase 3 — Synthetic data
Master data → relationships → transactions → controlled scenarios

### Phase 4 — Curated layer
Raw → Clean → Validate → Business-ready

### Phase 5 — Semantic View
Logical tables → Relationships → Dimensions → Facts → Metrics → Instructions → Verified queries

### Phase 6 — Evaluation
Golden Questions → Verified Queries → Evaluation → Fix semantic weaknesses → Re-test

### Phase 7 — Investigation
Agent → Governed analytical tools → Investigation workflow → Evidence

### Phase 8 — Product
Streamlit → Chat → Investigation → Impact Explorer → Evidence

### Phase 9 — Finalist hardening
Failure testing → Evaluation → Cost review → Demo rehearsal → Documentation → GitHub cleanup → Submission

## 32. Definition of Done

### Data
- Synthetic data is reproducible.
- Referential integrity is validated.
- Deliberate disruption scenarios exist.
- Fact grains are tested.

### Semantics
- Business entities are governed.
- Relationships are correct.
- Metrics have authoritative definitions.
- Inventory is modeled as semi-additive.
- Verified questions exist.

### AI
- Direct analytics work.
- Investigation works.
- Impact analysis works.
- Unsupported questions fail safely.

### Trust
- Important results are traceable to evidence.
- Metric definitions are visible.
- Supplier attribution is not overstated.
- Causal claims stay within available lineage.

### Application
- Product experience is coherent.
- Impact Explorer demonstrates ontology value.
- Evidence is accessible.

### Evaluation
- Golden Question Set exists.
- Evaluation has been run.
- Failures have been investigated.
- Regression is controlled.

### Delivery
- GitHub repository is reproducible.
- No secrets are committed.
- README explains the architecture.
- Demo scenario is deterministic.
- Final submission assets are ready.

## 33. Final Architecture Principle

```text
                     BUSINESS QUESTION
                            │
                            ▼
                   GOVERNED BUSINESS
                       SEMANTICS
                            │
             ┌──────────────┴──────────────┐
             ▼                             ▼
       DIRECT ANALYTICS              INVESTIGATION
       Cortex Analyst                 Cortex Agent
             │                             │
             └──────────────┬──────────────┘
                            ▼
                    SNOWFLAKE DATA
                            │
                            ▼
                     EVIDENCE + RESULT
                            │
                            ▼
                     CHAINLOOM UX
```

The architecture exists to preserve the chain:

**Business meaning → governed data → AI reasoning → evidence → decision support.**
