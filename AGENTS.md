# ChainLoom — AI Agent Instructions

## 1. Project Mission

ChainLoom is a Snowflake-native supply-chain intelligence application for the Snowflake CoCo CLI GCC Edition hackathon.

Problem Statement:

> Supply Chain Ontology and Governed Conversational Analytics

The goal is a governed industry ontology and semantic layer over fragmented supply-chain data, deployed as a working Streamlit Control Tower on Snowflake Container Runtime.

---

## 2. Current Implementation

The application is deployed and functioning. Key facts:

- **Entry point:** `streamlit/Home.py` (single-file Streamlit application)
- **Runtime:** Snowflake Container Runtime with OAuth session token authentication
- **AI integration:** Cortex Analyst REST API (`/api/v2/cortex/analyst/message`)
- **Semantic view:** `CHAINLOOM.SEMANTIC.CHAINLOOM_ANALYTICS`
- **Database:** `CHAINLOOM` with schemas `RAW`, `CURATED`, `SEMANTIC`
- **Curated surfaces:** 6 analytical views (V_SUPPLIER_PERFORMANCE, V_INVENTORY_POSITION, V_PRODUCTION_PERFORMANCE, V_CUSTOMER_FULFILLMENT, V_SHIPMENT_PERFORMANCE, V_PRODUCT_RISK_SIGNALS)
- **Semantic model:** 11 logical tables, 14 relationships, 12 governed metrics
- **Verified queries:** Q1–Q10 (operational), Q13 (product risk signals)
- **Governance boundary checks:** Q11 (causal boundary), Q12 (attribution boundary)

---

## 3. Critical Files — Do Not Casually Change

| File | Reason |
|------|--------|
| `sql/04_semantic/01_create_semantic_view.sql` | Core semantic model with all metrics, relationships, verified queries, and AI generation instructions |
| `streamlit/Home.py` | Deployed application — any change requires redeployment |
| `sql/02_raw/04_generate_transactions.sql` | Deterministic synthetic data with embedded disruption scenario |
| `sql/02_raw/06_final_refine_order_shipment.sql` | Final data refinement ensuring scenario coverage |
| `sql/03_curated/v_product_risk_signals.sql` | Product risk signal synthesis view |

---

## 4. Core Business Model

Entities: Supplier, Part, Product, Plant, Customer, Carrier, Date.

RAW layer includes bridge tables (SUPPLIER_PART, PRODUCT_PART) and transactional facts (PURCHASE_ORDER_LINE, SUPPLY_RECEIPT, INVENTORY, PRODUCTION, QUALITY, ORDER_LINE, SHIPMENT).

The curated layer aggregates RAW into five independent analytical surfaces plus a product-level risk signal summary. The semantic view exposes these as 11 logical tables with conformed dimensions.

---

## 5. Governance Constraints

These constraints are enforced in the semantic view and application. Do not weaken them.

1. **No fact-to-fact joins.** Each question is answered from a single analytical surface joined only to dimension tables.
2. **Inventory is semi-additive.** Snapshot quantities can be summed across parts/plants for one date but must not be summed across dates.
3. **No causal inference.** Lot/batch genealogy is unavailable. Do not claim that a supplier delay caused a customer shipment delay.
4. **RISK_SIGNAL_COUNT is a co-occurrence count (0–3), not a weighted or composite risk score.**
5. **P104_EXPOSURE_FLAG indicates BOM dependency, not proof of shortage or causality.**
6. **Missing metrics are preserved as NULL/unavailable.** Never silently convert to zero.
7. **AI does not invent formulas.** All metric definitions come from the governed semantic layer.

---

## 6. Semantic Layer Rules

The semantic layer is a core product artifact. It contains entities, relationships, dimensions, facts, metrics, business definitions, synonyms, instructions, and verified queries.

Business metrics have a single authoritative definition. Do not define the same metric differently in different parts of the application.

The current 12 governed metrics are defined in `sql/04_semantic/01_create_semantic_view.sql`. Any metric change must be made there first and propagated consistently.

---

## 7. Technology Stack

- Snowflake (database, compute, semantic views, Container Runtime)
- Cortex Analyst (governed NL analytics via REST API)
- Streamlit (application UI)
- Python (application logic)
- SQL (data model, curated views, semantic view)
- Git / GitHub (version control, deployment via Snowflake Git Repository)

Do not introduce external technologies without clear justification.

---

## 8. Security and Governance

- Never commit credentials, tokens, passwords, private keys or secrets.
- Never hardcode Snowflake credentials in application code.
- The application authenticates via Container Runtime OAuth token, not embedded credentials.
- Respect Snowflake RBAC.
- Do not bypass access controls for convenience.

---

## 9. Cost Discipline

The project has a limited Snowflake credit budget.

Avoid: unnecessarily large warehouses, repeated expensive queries, uncontrolled data generation, unnecessary model calls, expensive polling loops.

---

## 10. Testing and Evaluation

Verified queries (Q1–Q10, Q13) serve as the primary evaluation mechanism. Governance boundary checks (Q11, Q12) test that the system correctly refuses unsupported causal claims.

Evaluation should measure:
1. Correct business intent interpretation
2. Correct semantic entity selection
3. Correct governed metric usage
4. Logically correct SQL
5. Expected result
6. Appropriate handling of unsupported questions

---

## 11. Agent Authority

AI coding agents may:
- Inspect the repository
- Implement clearly defined requirements
- Write tests
- Refactor code when behavior is preserved
- Improve documentation
- Diagnose implementation errors

AI coding agents must NOT independently change:
- Core ontology or metric definitions
- Semantic view structure
- Governance constraints
- Security model
- Technology strategy

without explicitly flagging the change for review.

If an architectural decision is unclear, ask rather than guess.

---

## 12. Source of Truth

When there is a conflict:

1. Current Snowflake official documentation
2. `sql/04_semantic/01_create_semantic_view.sql` (the deployed semantic model)
3. `streamlit/Home.py` (the deployed application)
4. Project documentation in `docs/`
5. This file (AGENTS.md)
6. Conversation context

Agent assumptions must never override the deployed implementation or explicit project decisions.

---

## 13. Code Quality

Prefer: simple designs, small functions, clear naming, type hints where useful, explicit error handling, testable code, minimal dependencies, clear SQL, reusable components.

Avoid: clever but opaque code, unnecessary abstractions, duplicated business logic, hardcoded business metrics, magic values, hidden side effects.

---

## 14. Git Discipline

Use small, meaningful commits. Examples:

- `feat: add supply chain schema`
- `feat: add semantic view`
- `fix: correct OTD metric eligibility filter`
- `docs: align architecture with implementation`

Do not commit: credentials, local secrets, temporary files, generated caches.

---

## 15. Final Principle

ChainLoom should feel like a real enterprise product built on Snowflake, not a collection of AI-generated hackathon features.

Build with purpose. Build with evidence. Build with governance. Build for trust.
