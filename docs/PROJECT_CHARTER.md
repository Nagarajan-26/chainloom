# ChainLoom — Project Charter

**Status:** Architecture Approved / Model Hardened
**Version:** 1.1
**Problem Statement:** Supply Chain Ontology and Governed Conversational Analytics

## 1. Purpose

ChainLoom is a Snowflake-native supply-chain intelligence application designed for the hackathon problem statement:

> Build an industry ontology and a business entity/relationship model, expressed as governed semantic views, so that a natural-language layer returns consistent, trustworthy answers grounded in shared definitions and metrics.

ChainLoom connects supply-chain entities and operational facts so users can move from a business question to governed analytics, investigation, impact analysis and evidence.

## 2. Product Vision

ChainLoom provides a shared, governed understanding of:
- Suppliers
- Parts
- Products
- Plants
- Inventory
- Purchase-order commitments
- Supply receipts
- Customers
- Orders
- Shipments
- Carriers

The product should answer both direct analytical questions and multi-step questions such as:

> Why did delivery performance decline, what supply-chain path contributed to the deterioration, and which customers are confirmed or potentially at risk?

## 3. Core Differentiator

ChainLoom is not intended to be a generic chatbot over tables.

Its core differentiator is:

**Business meaning → governed semantics → relationship-aware analysis → evidence-backed answer.**

## 4. Scope

### In scope
- Synthetic supply-chain data
- Governed business ontology
- Explicit business relationships
- Governed metrics
- Snowflake Semantic Views
- Natural-language analytical queries
- Verified question/evaluation set
- Multi-step investigation
- Supply-chain impact exploration
- Evidence/provenance presentation
- Streamlit product experience
- GitHub-based engineering workflow

### Out of scope
- Real production or confidential data
- Lot/batch genealogy
- Autonomous procurement
- Autonomous order modification
- Full enterprise ERP integration
- Production-scale streaming platform
- Full ML forecasting platform
- Warehouse/bin-level inventory management

The MVP intentionally uses **Plant as the inventory location grain**.

## 5. Core Scenario

Supplier S017 → delayed supplier commitments / supply receipts → affected part P104 → inventory deterioration at PL03 → production constraint → order exposure → shipment delays → customer impact.

The synthetic dataset must contain deterministic ground truth so the scenario can be independently verified.

## 6. Product Modes

### Governed Analytics
- What is our OTD?
- What is OTD by supplier?
- Which plant has the highest shipment delay rate?
- What is the fill rate?

### Investigation
- Why did OTD decline?
- Which supplier or plant contributed most?
- Which customers are confirmed impacted?
- Which customers are at risk?
- Which alternate suppliers can provide an affected part?

## 7. Trust Principles

ChainLoom distinguishes:
- Observed facts
- Governed metrics
- Derived analytical findings
- Potential risk
- Causal claims

The MVP does not claim exact receipt-to-shipment causality because it does not implement lot/material genealogy.

## 8. Success Criteria

1. Ontology represented in Snowflake.
2. Metrics have authoritative definitions.
3. Natural-language questions produce consistent answers.
4. Multi-hop relationships support impact analysis.
5. Important answers can be traced to evidence.
6. Controlled disruption is reproducible.
7. A judge can understand the product through a short reliable demo.
8. Repository and Snowflake implementation are reproducible.

## 9. Delivery Philosophy

- Correctness over feature count
- Current Snowflake capabilities
- Deterministic synthetic scenarios
- Explicit metric definitions and grain
- Small, testable increments
- Evidence over unsupported AI claims
