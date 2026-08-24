# ChainLoom — System Architecture

**Status:** Architecture Approved  
**Version:** 1.0  
**Problem Statement:** Supply Chain Ontology and Governed Conversational Analytics  
**Architecture Target:** Snowflake 2026 platform

## 1. Architecture Objective

ChainLoom is a Snowflake-native governed supply-chain intelligence application providing:
1. Governed natural-language analytics.
2. A shared supply-chain ontology.
3. Consistent business metrics.
4. Multi-step investigation.
5. Relationship-aware impact analysis.
6. Evidence and provenance.
7. Repeatable evaluation.
8. A polished product experience.

The architecture separates physical data, curated business data, semantic meaning, AI orchestration and product presentation.

## 2. Architecture Principles

### 2.1 Snowflake is the system of record
Supply-chain data, semantic definitions, metrics, AI objects and evaluation artifacts should remain within Snowflake wherever practical.

### 2.2 The Semantic View is the governed business contract
It defines logical tables, relationships, dimensions, facts, metrics, descriptions, useful synonyms/instructions and verified queries.

### 2.3 Physical data and semantic data are different layers

```text
Physical Model
→ Curated Business Model
→ Semantic View
→ AI
```

### 2.4 Facts retain explicit grain
Every fact has explicit grain. Cross-fact metrics must not be calculated by blindly joining raw fact tables.

### 2.5 AI must not invent business definitions
Business metrics and relationships are deterministic. AI interprets questions and explains results; it does not invent metric formulas, evidence, relationships or data values.

### 2.6 Investigation is evidence-driven
ChainLoom distinguishes observed fact, derived metric, analytical conclusion and potential risk.

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
For direct metric, filtering, comparison and dimensional questions.

### Investigation
For multi-step questions requiring relationship traversal, impact analysis and evidence assembly.

## 5. Cortex Analyst Role

Cortex Analyst handles governed structured-data analytics over the ChainLoom Semantic View:
- Natural-language analytical queries
- Metric queries
- Dimensional analysis
- Filtering
- Comparisons
- Aggregations
- Verified-question workflows

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

Simple questions should use the simpler governed analytical path where practical.

## 7. Current Cortex Agent / Semantic View Architecture

The implementation must follow current Snowflake behavior.

Cortex Agents can use Semantic Views as structured-data tools. Current behavior has evolved from older patterns, so application code must not assume an Agent invocation necessarily delegates SQL generation to a separate Cortex Analyst service.

Use current Agent response structures and current Snowflake documentation when implementing.

## 8. Data Architecture

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

### Facts
```text
FACT_SUPPLY_RECEIPT
FACT_INVENTORY
FACT_PRODUCTION
FACT_ORDER_LINE
FACT_SHIPMENT
FACT_QUALITY
```

## 9. Data Layering

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

RAW contains generated source-like data.

CURATED contains validated business data and deterministic transformations.

SEMANTIC contains Snowflake Semantic Views with entities, relationships, facts, dimensions, metrics, instructions and verified queries.

## 10. Proposed Snowflake Database Structure

```text
CHAINLOOM
│
├── RAW
├── CURATED
├── SEMANTIC
├── ANALYTICS
└── APP
```

Exact physical schema names may be adjusted if account permissions or platform constraints require it.

## 11. Semantic View Boundary

Initial business-facing concepts:
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

## 12. Relationship Strategy

```text
Supplier → Supply Receipt
Supplier → Supplier-Part
Part → Supply Receipt
Part → Product-Part
Product → Product-Part
Product → Order Line
Plant → Inventory
Plant → Production
Plant → Order Line
Customer → Order Line
Order Line → Shipment
Carrier → Shipment
```

Many-to-many relationships use explicit bridge entities.

## 13. Supplier Attribution

Supplier capability:
```text
Supplier
→ BRIDGE_SUPPLIER_PART
→ Part
```

Actual supply:
```text
Supplier
→ FACT_SUPPLY_RECEIPT
→ Part
→ Plant
```

Supplier-Part capability must never be treated as proof of downstream causality.

## 14. Metric Computation Architecture

Metrics are calculated at natural grain.

```text
FACT_SHIPMENT
      ↓
Shipment-grain aggregation
      ↓
OTD / Late Shipment Count
```

```text
FACT_SUPPLY_RECEIPT
      ↓
Receipt-grain aggregation
      ↓
Supplier Inbound OTD
```

```text
FACT_INVENTORY + Demand History
      ↓
Part × Plant × Date
      ↓
Inventory Coverage Days
```

```text
FACT_ORDER_LINE
      ↓
Order-line aggregation
      ↓
Fill Rate / At-Risk Orders
```

Raw fact-to-fact joins must not be used without controlling grain.

## 15. Investigation Architecture

Example:

```text
Question: Why did OTD decline?

1. Calculate current OTD.
2. Calculate comparison-period OTD.
3. Identify dimensions with material deterioration.
4. Identify strongest contributor.
5. Trace relevant relationships.
6. Quantify observed changes.
7. Produce evidence-backed explanation.
```

## 16. Impact Analysis Architecture

### Confirmed impact
Observed operational fact, such as a delayed shipment.

### Potential risk
Deterministic risk condition, such as:

```text
Open Order
+
Supply dependency
+
Insufficient inventory coverage
+
Promised-date exposure
```

Confirmed impact and potential risk must not be merged.

## 17. Impact Explorer

The application should visually represent governed relationship paths such as:

```text
Supplier S017
      │
      ├── Part P104
      │       │
      │       └── Plant PL03
      │               │
      │               ├── Inventory ↓
      │               ├── Production ↓
      │               └── Orders exposed
      │
      └── Part P205
              │
              └── Plant PL07
```

## 18. Evidence Architecture

Important answers should be traceable through:

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

## 19. Verified Query Strategy

Maintain a Golden Question Set covering:
- Basic metrics
- Dimensional analytics
- Relationship questions
- Multi-hop questions
- Investigation
- Impact
- Unsupported/boundary questions

Verified queries support runtime quality and evaluation.

## 20. Cortex Analyst Evaluation

Evaluation should measure:
- SQL correctness
- Result correctness
- Semantic interpretation
- Regression
- Latency

Verified queries can serve as ground truth for evaluation.

## 21. Application Architecture

Initial product components:

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

The structure may be simplified during implementation. Avoid premature abstraction.

## 22. Streamlit Deployment

Preferred product target: Streamlit in Snowflake.

Use the runtime supported by the hackathon account and current Snowflake capabilities. Do not introduce unnecessary infrastructure merely to use a particular runtime.

## 23. Git and Development Architecture

GitHub is the engineering source of truth.

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

Codex is primarily used for repository/software engineering. Snowflake-native AI assistance is used for Snowflake-specific development and exploration where useful.

## 24. Security

Never commit passwords, tokens, private keys, API secrets or connection credentials.

Synthetic data must contain no real personal or confidential information.

## 25. Cost Architecture

Controls:
- Small development warehouse
- Auto-suspend
- Controlled synthetic-data volume
- Avoid repeated full-table scans
- Cache application results where appropriate
- Avoid unnecessary agent calls
- Monitor credit usage

Increase compute only when evidence shows it is necessary.

## 26. Failure Handling

Unsupported questions should explain that the governed model lacks sufficient information.

Ambiguous questions should request clarification.

Query failures must not result in fabricated answers.

Missing evidence must not result in unsupported confidence.

Agent failures should use a simpler governed analytical path where possible.

## 27. Observability

Retain enough information to debug:
- User question
- Selected workflow
- Semantic concept
- Generated SQL
- Query ID where available
- Execution result
- Response status
- Evaluation outcome

Do not log secrets.

## 28. Architecture Boundaries

Initial ChainLoom does not include:
- External ERP integration
- Real production data
- Autonomous procurement
- Autonomous order modification
- Production-scale streaming
- Full ML forecasting platform
- Microservice infrastructure

## 29. Implementation Sequence

### Phase 1 — Snowflake foundation
Database → Schemas → Warehouse → Tables → Validation

### Phase 2 — Synthetic data
Master data → Relationships → Transactions → Controlled scenarios

### Phase 3 — Curated layer
Raw → Clean → Validate → Business-ready

### Phase 4 — Semantic View
Logical tables → Relationships → Dimensions → Facts → Metrics → Instructions → Verified queries

### Phase 5 — Evaluation
Golden Questions → Verified Queries → Evaluation → Fix semantic weaknesses → Re-test

### Phase 6 — Investigation
Agent → Governed analytical tools → Investigation workflow → Evidence

### Phase 7 — Product
Streamlit → Chat → Investigation → Impact Explorer → Evidence

### Phase 8 — Finalist hardening
Failure testing → Evaluation → Cost review → Demo rehearsal → Documentation → GitHub cleanup → Submission

## 30. Definition of Done

### Data
- Synthetic data is reproducible.
- Referential integrity is validated.
- Deliberate disruption scenarios exist.

### Semantics
- Business entities are governed.
- Relationships are correct.
- Metrics have authoritative definitions.
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

## 31. Final Architecture Principle

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
