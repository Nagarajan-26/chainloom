# ChainLoom — AI Agent Instructions

## 1. Project Mission

ChainLoom is a finalist-targeted hackathon project for the Snowflake CoCo CLI GCC Edition.

Problem Statement:

> Supply Chain Ontology and Governed Conversational Analytics

The goal is to build a high-quality, Snowflake-native supply-chain intelligence application that creates a governed industry ontology and semantic layer over fragmented supply-chain data.

ChainLoom should allow users to:

1. Ask natural-language questions about supply-chain operations.
2. Receive answers grounded in governed business definitions and metrics.
3. Investigate the causes behind important metric changes.
4. Traverse business relationships to understand downstream impact.
5. Provide evidence and provenance for important answers.

ChainLoom is NOT intended to be a generic chatbot or a simple natural-language-to-SQL demo.

---

## 2. Product Vision

ChainLoom follows this journey:

ASK → UNDERSTAND → INVESTIGATE → TRACE IMPACT → PROVE

The central product principle is:

> Do not merely answer the question. Understand the business relationship behind it, investigate the cause, quantify downstream impact, and show why the answer can be trusted.

The primary differentiator is governed semantic understanding combined with relationship-aware investigation.

---

## 3. Core Business Model

The initial ontology should focus on a manageable but meaningful supply-chain model.

Core entities:

- Supplier
- Part
- Plant
- Product
- Customer
- Order
- Shipment
- Carrier
- Inventory

Core relationships include, where appropriate:

- Supplier supplies Part
- Part is associated with Product
- Plant manufactures Product
- Customer places Order
- Order contains Product/Part
- Order is fulfilled by Shipment
- Carrier transports Shipment
- Shipment is delivered to Customer
- Plant holds/manages Inventory

The ontology must be implemented as a real governed semantic model in Snowflake rather than existing only as application documentation.

---

## 4. Core Product Capabilities

The MVP must support the following capabilities.

### 4.1 Governed Conversational Analytics

Users can ask questions such as:

- What is our current On-Time Delivery?
- Which suppliers are underperforming?
- Compare supplier performance.
- Which plants have the highest shipment delays?

Answers must be grounded in the governed semantic layer.

### 4.2 Investigation

The system should be capable of investigating questions such as:

> Why did On-Time Delivery decline?

The investigation should identify meaningful contributors rather than generate an unsupported narrative.

A typical investigation may follow:

Metric deviation
→ dimension analysis
→ largest contributor
→ related entity
→ supporting evidence

### 4.3 Impact Analysis

The system should support questions such as:

> Supplier S17 is experiencing delays. Which customers are affected?

The system should traverse governed relationships such as:

Supplier
→ Part
→ Plant
→ Order
→ Shipment
→ Customer

The result should quantify impact where the underlying data supports it.

### 4.4 Evidence / Provenance

Important answers should expose supporting information such as:

- Business metric definition
- Relevant semantic entity
- Verified query where applicable
- Generated SQL where useful
- Supporting data
- Data freshness
- Relevant source tables

The system must never fabricate evidence.

---

## 5. Technology Principles

Snowflake is the primary data and AI platform.

Prefer Snowflake-native capabilities when they directly address the requirement.

Expected technologies may include:

- Snowflake
- Semantic Views
- Cortex Analyst
- Cortex Agents
- Cortex Code / CoCo
- Verified Queries
- Streamlit
- Python
- SQL
- Git / GitHub

Do not introduce external technologies merely for novelty.

Every additional technology must have a clear architectural or product justification.

---

## 6. Snowflake Version and Documentation Rule

This project targets the current Snowflake platform available during the 2026 hackathon.

Before implementing Snowflake-specific functionality, verify the current official Snowflake documentation whenever the feature or syntax may have changed.

Do not rely on old tutorials or outdated syntax when current documentation is available.

Prefer:

- GA capabilities over preview capabilities
- Current Semantic View syntax
- Current Cortex Analyst capabilities
- Current Cortex Agent capabilities
- Current Cortex Code / CoCo capabilities

If a preview feature is considered, explicitly identify it as preview and evaluate whether it is safe and available for the hackathon environment before using it.

Never invent Snowflake syntax.

---

## 7. Semantic Layer Rules

The semantic layer is a core product artifact, not an implementation detail.

It must contain meaningful:

- Entities
- Relationships
- Dimensions
- Facts
- Metrics
- Business definitions
- Synonyms where useful
- Instructions where useful
- Verified queries

Business metrics must have a single authoritative definition within ChainLoom.

Do not define the same metric differently in different parts of the application.

For example, if On-Time Delivery is defined as:

Eligible shipments delivered within the promised delivery window
divided by
total eligible shipments

that definition must remain consistent across:

- Semantic Views
- SQL
- Agent skills
- UI
- Documentation
- Evaluation

---

## 8. Verified Query and Evaluation Rules

Verified queries are a critical part of ChainLoom's trust and accuracy strategy.

Create a curated Golden Question Set containing representative business questions.

Each important question should have:

- Natural-language question
- Expected business intent
- Expected metric/entity
- Expected result or validation logic
- Verified query where applicable

Do not create verified queries merely to increase their count.

They must represent meaningful user questions.

Evaluation should measure whether the system:

1. Understands the business intent.
2. Uses the correct semantic entities.
3. Uses the correct governed metrics.
4. Generates logically correct SQL.
5. Produces the expected result.

---

## 9. AI / Agent Architecture

Avoid a single monolithic prompt whenever specialized capabilities are appropriate.

Potential ChainLoom skills include:

- Supply Chain Query
- Investigation
- Impact Analysis
- Evidence / Provenance
- Recommendation, if justified after the core MVP is complete

Skills should have clear responsibilities.

The orchestrator should decide which capability is appropriate rather than forcing every question through every skill.

Do not build unnecessary agents.

Agentic behavior must have a clear purpose.

---

## 10. Hallucination and Trust Rules

The application must prefer refusing or qualifying an answer over inventing information.

If the governed data does not contain enough information to answer a question, ChainLoom should clearly communicate that limitation.

Never fabricate:

- Metrics
- SQL
- Evidence
- Sources
- Data freshness
- Business definitions
- Recommendations presented as facts

Generated explanations must be grounded in actual query results.

---

## 11. Data Rules

Use synthetic data only unless the hackathon explicitly provides an approved alternative.

Synthetic data should be:

- Referentially consistent
- Realistic
- Sufficiently rich for investigation
- Designed around deliberate supply-chain scenarios

Prefer meaningful synthetic scenarios over massive random datasets.

Important scenarios may include:

- Supplier disruption
- Plant bottleneck
- Shipment delays
- Inventory shortage
- Demand spike
- Quality issue

Data should allow ChainLoom to demonstrate clear cause-and-effect relationships.

---

## 12. Security and Governance

Never commit credentials, tokens, passwords, private keys or secrets.

Never hardcode Snowflake credentials.

Respect Snowflake RBAC and existing governance controls.

Do not bypass access controls for convenience.

Do not copy sensitive or private data into the repository.

Do not create insecure shortcuts merely to make a demo work.

---

## 13. Cost Discipline

The project has a limited Snowflake credit budget.

Prefer efficient development practices.

Avoid:

- unnecessarily large warehouses
- repeated expensive queries
- uncontrolled synthetic-data generation
- unnecessary model calls
- expensive polling loops

Use the smallest practical compute for development and testing.

Before introducing an expensive workload, assess whether a cheaper approach can provide the same result.

Cost should be monitored throughout development rather than only at the end.

---

## 14. Application Principles

The Streamlit/application layer should demonstrate the product rather than merely expose a chat box.

The UI should make the following concepts visible where appropriate:

- Supply-chain health
- Governed metrics
- Investigation flow
- Entity relationships
- Downstream impact
- Evidence / provenance

Prioritize clarity and usefulness over visual complexity.

Do not add UI features that do not contribute to the core product story.

---

## 15. Testing Requirements

Testing is mandatory.

At minimum, test:

### Functional correctness

Does the application perform the intended workflow?

### Semantic correctness

Does the natural-language question map to the correct business concept?

### SQL correctness

Does generated SQL correctly represent the requested analysis?

### Result correctness

Does the answer match the expected result?

### Consistency

Do different phrasings of the same business question produce consistent answers?

### Failure handling

Does the application appropriately handle unsupported questions?

### Trust

Can important answers be traced to supporting data?

---

## 16. Development Workflow

Follow this workflow:

PLAN → IMPLEMENT → TEST → REVIEW

Do not make broad architectural changes without first understanding the existing project documentation.

Before modifying an existing component:

1. Read the relevant documentation.
2. Inspect the existing implementation.
3. Understand dependencies.
4. Make the smallest appropriate change.
5. Test the change.
6. Report what changed.

Prefer incremental changes over large rewrites.

---

## 17. Agent Authority

AI coding agents may:

- Inspect the repository.
- Create implementation files.
- Implement clearly defined requirements.
- Write tests.
- Refactor code when behavior is preserved.
- Improve documentation.
- Diagnose implementation errors.

AI coding agents must NOT independently change:

- Product scope
- Core ontology
- Core business definitions
- Metric definitions
- Overall architecture
- Security model
- Data governance approach
- Technology strategy

without explicitly flagging the change for human/architect review.

If an architectural decision is unclear, STOP and ask for clarification rather than inventing one.

---

## 18. Source of Truth

The project documentation and approved implementation are the source of truth.

Do not rely on conversation memory for critical architectural decisions.

When there is a conflict:

1. Current approved project documentation
2. Current Snowflake official documentation
3. Existing tested implementation
4. Conversation context
5. Agent assumptions

Agent assumptions must never override explicit project decisions.

---

## 19. Code Quality

Prefer:

- Simple designs
- Small functions
- Clear naming
- Type hints where useful
- Explicit error handling
- Testable code
- Minimal dependencies
- Clear SQL
- Reusable components

Avoid:

- Clever but opaque code
- unnecessary abstractions
- duplicated business logic
- hardcoded business metrics
- magic values
- hidden side effects

Business logic should be easy for another engineer to understand.

---

## 20. Git Discipline

Use small, meaningful commits.

Examples:

- `chore: initialize ChainLoom project`
- `feat: add supply chain schema`
- `feat: add semantic view`
- `feat: add verified queries`
- `feat: add investigation workflow`
- `feat: add impact analysis`
- `feat: add Streamlit application`
- `test: add golden question evaluation`

Do not commit:

- credentials
- local secrets
- temporary files
- generated caches
- unnecessary large datasets

---

## 21. Hackathon Priority

The ultimate goal is not maximum code.

The goal is a technically strong, complete and convincing finalist submission.

Every implementation decision should be evaluated against:

1. Technical Execution
2. Real-World Relevance
3. Solution Completeness

Prefer depth over superficial feature count.

A small capability that works reliably and can be demonstrated clearly is more valuable than a large capability that is unstable.

---

## 22. Agent Behavior

Be proactive but disciplined.

Before implementing:

- inspect the repository
- read relevant project documentation
- understand existing decisions

During implementation:

- keep changes focused
- validate assumptions
- test important behavior
- report blockers clearly

When something fails:

1. Diagnose the actual error.
2. Do not hide the error.
3. Do not fabricate a successful result.
4. Attempt a grounded fix.
5. Re-test.

When a requirement is ambiguous:

> Ask rather than guess.

When a proposed feature is outside scope:

> Flag it before implementing.

When a better architectural approach is identified:

> Explain the trade-off and request approval before changing the architecture.

---

## 23. Final Principle

ChainLoom should feel like a real enterprise product built on Snowflake, not a collection of AI-generated hackathon features.

Build with purpose.

Build with evidence.

Build with governance.

Build for trust.

Build for the finalist round.