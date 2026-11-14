# ChainLoom — Finale Pitch & Demo Script

**Total:** 15 minutes — 10-minute pitch + 5-minute judge Q&A  
**Pitch split:** 2-minute story, 5-minute slides, 3-minute live demo

## 1. Story — 2 minutes

ChainLoom is a Snowflake-native supply-chain Control Tower. Supply-chain data is fragmented across procurement, inventory, production, fulfillment and logistics. A natural-language interface alone is not enough: it can produce plausible answers while joining incompatible grains or implying causes that the data cannot prove.

ChainLoom connects these domains through independent curated analytical surfaces and a governed Snowflake Semantic View. Its purpose is not only to answer business questions, but to make the analytical boundaries visible — what the data supports and what it does not.

## 2. Slides — 5 minutes

1. **Problem and solution (1 min):** fragmented supply-chain evidence; one governed analytical experience.
2. **Architecture (1 min):** RAW → CURATED → SEMANTIC → Streamlit; Snowflake-native components.
3. **Data model (1 min):** independent analytical surfaces with explicit grains; avoid unsupported fact-to-fact joins and snapshot aggregation.
4. **Intelligence and governance (1 min):** Semantic View, governed metrics, verified queries, and explicit rules against unsupported causal claims.
5. **CoCo CLI contribution and value (1 min):** explain the actual development tasks performed with CoCo CLI, with concrete examples from the team's real workflow. Cortex Analyst powers natural-language analytics at runtime; CoCo CLI was the development assistant.

## 3. Live demo — 3 minutes

### Demo A — business question (about 90 seconds)

Ask: **Which carriers have the lowest on-time delivery rate?**

Show the generated SQL and result. Point out the eligible-shipment denominator and that the query uses the shipment analytical surface.

### Demo B — governance boundary (about 90 seconds)

Use the P104 question for the supported data period:

**For August 2026, which products with Part P104 BOM exposure also had constrained production days, and what can the data establish about causation?**

Show the observed exposure/constraint evidence, then explain that co-occurrence is not proof of causation. The current data does not contain lot/batch genealogy linking a specific shortage to a production event.

**Demo safety:** Do not present an empty result or a failed SQL execution as proof that governance blocked a claim. Distinguish successful execution, zero rows, SQL generation failure and execution failure. If the live boundary test is unstable, show the prevalidated result/evidence and explain the limitation honestly.

## 4. Closing (10–15 seconds, within the allotted sections)

ChainLoom demonstrates governed conversational analytics: not just generating answers, but making clear what the underlying evidence can and cannot establish.

## Presenter notes

- The synthetic transaction generator covers July 1–August 31, 2026. Avoid relative phrases such as “last month”; name the supported period explicitly.
- Do not claim that CoCo CLI runs the end-user question. The application calls the Cortex Analyst REST API at runtime.
- Do not claim P104 caused production constraints. P104 exposure means BOM dependency only.
- Do not claim supplier delays caused customer shipment delays; lot/batch genealogy is unavailable.
