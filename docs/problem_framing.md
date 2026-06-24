Problem Framing Document
Project: Retail Pricing Operations — AI Support Agent

Version: 1.1

Author: Arikh Akher

1. Business Context
A B2B SaaS retail pricing platform serves enterprise customers including global fashion, home improvement, and specialty retail brands. The platform generates pricing plans across multiple dimensions — region, market, channel, product hierarchy, and season — processing hundreds of thousands of material-price combinations per run.
When a pricing run completes, non-technical users have no self-service way to investigate why certain materials are missing from the output. Every investigation requires a developer to manually query the database and examine system logs. Timezone differences between the support team and customers add hours to resolution time.

2. Primary User Personas
Persona A — Pricing Planner (Primary User)

Builds pricing plans by selecting: Region, Market, Channel, Product Hierarchy, Season, and Materials
Submits the plan for price generation
Reviews output in the UI — all generated materials and prices are shown with green indicators
Non-technical. Cannot query databases or read system logs
Core pain: Selected materials silently disappear from output. Planner notices the count is wrong — expected 500 materials, sees 487. Has no way to find out why 13 are missing without calling a developer
Urgency: Moderate to high — missing materials block plan approval and downstream pricing cycles

Persona B — Pricing Manager (Secondary User)

Reviews and approves completed pricing plans
Relies on what the UI surface shows
Core pain: Cannot approve a plan with confidence if material counts look wrong or incomplete
Urgency: Approval blockers delay dependent systems — ERP, ecommerce, wholesale platforms


3. Problem Statement
When a pricing run completes, materials can silently disappear from the output for two distinct reasons:
Reason 1 — Rule Mismatch

The price generation engine evaluates each material against pricing rules before generating a price. If a material fails a rule, it is silently skipped — no error, no notification. Example: a material has a 3-month expiry date but the plan is generating prices for a 6-month horizon. The rule rejects it silently.
Reason 2 — Master Data Gap

A planner selects a Region, Market, Channel, and Product Hierarchy combination. But the material does not exist in the master data at that specific intersection. The planner believes they added it correctly. The system finds no matching record at that combination and silently skips it.
These two root causes require completely different corrective actions:
Root CauseWho ActsWhat They DoRule mismatchPricing PlannerAdjusts plan parameters or material selectionMaster data gapMaster Data TeamFixes the material mapping in master data
Currently, distinguishing between these two causes requires a developer to query the database and grep Cloud Function logs by material ID — a process that takes hours and requires timezone coordination.
The agent solves this by giving planners and managers a direct, accurate, self-service answer to: "Why is this material missing?" — without developer involvement.

4. Workflow The Agent Supports
Pricing run completes
        ↓
Planner reviews UI — notices material count mismatch
        ↓
Opens agent chat → asks in natural language
        ↓
Agent identifies question type:
  ├── Missing material query → checks rule evaluation status
  ├── Root cause triage     → rule mismatch vs master data gap
  └── Plan completeness     → how many materials priced vs selected
        ↓
Agent returns accurate, sourced answer with root cause
        ↓
If system failure detected (not rule, not data) → escalates to 
developer with structured context (plan name, material ID, error type)

5. Inputs, Outputs, Constraints
DetailInputsNatural language question, plan name, material ID, region, market, channel, seasonOutputsAccurate root cause answer grounded in simulated DB query resultData sourcesSimulated pricing database (SQLite for this build)ConstraintsAgent must never answer from assumption — only from queried dataOut of scopeAgent cannot modify plans, trigger runs, approve prices, or fix master data

6. Example User Questions

"I selected 500 materials in plan SUMMER_LATAM_V2 but only 487 are showing. Where are the missing 13?"
"Material M-4521 was selected in plan FALL_EU_2024 but it's not in the output. Why?"
"Is material M-3301 missing because of a rule problem or a data problem?"
"Which materials in plan WINTER_NA_2024 failed price generation and why?"
"Plan SPRING_LATAM_2024 is showing fewer materials than I selected. Can you check?"


7. Success Criteria
MetricTargetCorrect root cause identification≥ 90% on evaluation test setHallucination rate0% — agent never answers without querying dataCorrect tool selection≥ 95% — right tool for right question typeEscalation accuracy100% — system failures always escalated, never droppedRule mismatch vs data gap distinction≥ 90% correct classificationSensitive data in logs0% — no pricing values written to logs

8. Known Failure Cases & Edge Scenarios
Failure CaseExpected Agent BehaviourMaterial missing due to rule mismatchReport exact rule that failed, advise planner to adjust planMaterial missing due to master data gapReport mapping does not exist, advise contacting master data teamPlan name entered incorrectlyAsk for clarification, do not guess or assumeMaterial ID does not exist in systemReport clearly, do not fabricate a statusRoot cause is a system failure not rule or dataEscalate to developer with plan name, material ID, and anomaly descriptionUser asks agent to fix the master dataRefuse clearly, agent is read-onlyUser asks agent to re-run price generationRefuse clearly, agent cannot trigger system actionsStatus field returns NULL or unexpected valueReport as unknown, escalate — never guess

9. Safety Requirements

Read-only: Agent never modifies any data under any circumstance
Grounded answers only: Every answer sourced from a simulated DB query — never from LLM inference alone
Explicit uncertainty: If data is missing, ambiguous, or NULL — agent states this clearly
Escalation path: System anomalies trigger escalation tool with structured context
No fabrication: Agent never invents a reason for a missing material
PII-safe logging: No pricing values, customer names, or commercial data written to logs