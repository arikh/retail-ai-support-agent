Problem Framing Document
Project: Retail Pricing Operations — AI Support Agent

Version: 1.0

Author: Arikh Akher

1. Business Context
A B2B SaaS retail pricing platform serves enterprise customers including global fashion, home improvement, and specialty retail brands. The platform generates pricing plans across multiple regions (NA, LATAM, EU), seasons, and product catalogs — processing millions of price generations per run.
Support teams receive a high volume of repetitive operational queries from two primary user types, typically resolved only after developer intervention and database investigation. The timezone gap between the support team and customers increases resolution time significantly.

2. Primary User Personas
Persona A — Pricing Analyst

Creates pricing plans: selects materials, region, season, submits for generation
Non-technical. Cannot query databases or read system logs
Pain: Does not know if all selected materials were priced correctly after a run
Urgency: Occasionally needs answers during a live run. Frequently needs answers post-run before downstream systems consume the prices

Persona B — Pricing Manager

Reviews and approves generated pricing plans
Non-technical. Relies entirely on what the system surface shows them
Pain: Cannot approve a plan with confidence if they suspect missing or incorrect prices
Urgency: Approval blockers delay downstream client systems — ERP, ecommerce, wholesale platforms


3. Problem Statement
When a pricing run completes, analysts and managers have no self-service way to verify:

Whether all selected materials were priced
Whether prices were successfully downstreamed to client systems
Whether specific materials were correctly assigned to the expected season

Current resolution path requires emailing a developer, who manually queries the database, checks Cloud Function logs, and investigates Pub/Sub pipeline failures. With timezone differences, this adds hours to resolution time — during which downstream systems may be blocked or receiving incomplete data.
The agent solves this by giving non-technical users direct, accurate, database-grounded answers to operational pricing questions — without developer involvement.

4. Workflow The Agent Supports
Pricing run completes
        ↓
Analyst / Manager has a question about plan status
        ↓
Opens agent chat → asks in natural language
        ↓
Agent identifies question type:
  ├── Price generation status  → queries price status field in DB
  ├── Downstream status        → queries downstream status field in DB
  └── Season / material check  → queries plan-material mapping in DB
        ↓
Agent returns accurate, sourced answer
        ↓
If system anomaly detected → escalates to developer with context

5. Inputs, Outputs, Constraints
DetailInputsNatural language question, plan name, material ID, region, seasonOutputsAccurate status answer grounded in DB query resultData sourcesSimulated pricing database (SQLite for this build)ConstraintsAgent must never answer from assumption — only from queried dataOut of scopeAgent cannot modify plans, trigger runs, or approve prices

6. Example User Questions

"Has plan SUMMER_NA_2024 completed price generation for all materials?"
"Material ID M-4521 was selected in plan FALL_EU_2024 — was it priced?"
"Did the prices for plan SPRING_LATAM_2024 downstream to the client system?"
"Which materials in plan WINTER_NA_2024 are missing prices?"
"Is material M-3301 assigned to Season A or Season B in the current plan?"


7. Success Criteria
MetricTargetCorrect status answer rate≥ 90% on evaluation test setHallucination rate0% — agent must not answer without querying DBCorrect tool selection≥ 95% — right tool called for right question typeEscalation accuracy100% — system issues always escalated, never silently droppedPII / sensitive data in logs0 — plan names and material IDs logged, no customer pricing data

8. Known Failure Cases & Edge Scenarios
Failure CaseExpected Agent BehaviourMaterial exists in DB but price generation failedReport exact status, do not say "price generated"Plan name entered incorrectly by userAsk for clarification, do not guessDownstream status field is NULLReport as "status unknown", escalateUser asks agent to approve or modify a planRefuse clearly, explain agent is read-onlyUser asks why a price was not generatedAgent reports status, escalates root cause to developerSystem anomaly detected (missing records, unexpected NULLs)Escalate with context, never fabricate an answer

9. Safety Requirements

Read-only: Agent never modifies any data
Grounded answers only: Every answer sourced from a DB query result
Explicit uncertainty: If data is missing or ambiguous, agent says so clearly
Escalation path: System issues trigger escalation tool with structured context
PII-safe logging: No customer pricing values written to logs