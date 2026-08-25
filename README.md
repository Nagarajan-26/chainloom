# ChainLoom

> Governed conversational intelligence for supply-chain ontology, analytics and impact analysis.

ChainLoom is a Snowflake-native hackathon project for the **Supply Chain Ontology and Governed Conversational Analytics** problem statement.

## The problem

Supply-chain data is scattered across ERP, logistics, supplier and operational systems. Definitions are inconsistent, relationships are difficult to traverse, and the same natural-language question can produce different answers across teams.

## Our approach

ChainLoom creates a governed supply-chain ontology and semantic layer connecting:

```text
Supplier → Part → Product → Plant
                         ↓
                 Inventory / Production
                         ↓
                    Customer Order
                         ↓
                      Shipment
                         ↓
                      Customer
```

The system combines:
- Snowflake governed semantic modeling
- Natural-language analytics
- Relationship-aware investigation
- Supply-chain impact analysis
- Evidence-backed answers
- Repeatable evaluation

## Product idea

A user can ask:

> Why did delivery performance decline, and which customers are affected?

ChainLoom moves from:

```text
Metric
  ↓
Investigation
  ↓
Relationship traversal
  ↓
Impact
  ↓
Evidence
```

rather than returning an unsupported generic AI explanation.

## Initial scenario

A controlled synthetic disruption centered on Supplier S017 demonstrates:

```text
S017
 ↓
Delayed purchase-order commitments / supply receipts
 ↓
P104 availability
 ↓
PL03 inventory
 ↓
Production constraint
 ↓
Order exposure
 ↓
Shipment delays
 ↓
Customer impact
```

The scenario is synthetic and deterministic so results can be independently verified.

## Repository structure

```text
chainloom/
├── AGENTS.md
├── README.md
└── docs/
    ├── PROJECT_CHARTER.md
    ├── ONTOLOGY.md
    ├── METRICS.md
    └── ARCHITECTURE.md
```

## Current status

**Architecture hardened after independent CoCo review.**

Next stages:
1. Physical data model
2. Synthetic data
3. Curated layer
4. Semantic View
5. Verified questions and evaluation
6. Investigation workflow
7. Streamlit product
8. Finalist hardening

## Development principles

- Correctness over feature count.
- Current Snowflake capabilities.
- Explicit business definitions and grain.
- Deterministic synthetic scenarios.
- Evidence over unsupported AI claims.
- Small, testable increments.
- No secrets in GitHub.
