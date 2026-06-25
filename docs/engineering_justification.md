# Engineering & Product Justification

## Problem Statement

Retail pricing operations teams spend significant time manually investigating 
why materials are missing from pricing plans. The root causes — expiry rules, 
data inconsistencies, downstream failures — are buried across multiple systems. 
This agent centralises that investigation into a single conversational interface.

---

## Design Decisions

### 1. LangGraph ReAct over a simple LLM call

**Decision:** Use LangGraph's ReAct agent loop instead of a single LLM prompt.

**Justification:** Pricing queries require multi-step reasoning — first fetch the 
plan, then fetch missing materials, then explain the rejection rule. A single LLM 
call cannot reliably chain these steps. ReAct allows the agent to decide which 
tool to call at each step based on intermediate results.

**Tradeoff:** ReAct loops are slower and can loop infinitely. Mitigated with a 
recursion limit and graceful fallback message.

---

### 2. Groq + llama-3.3-70b-versatile over OpenAI

**Decision:** Use Groq inference with llama-3.3-70b-versatile.

**Justification:** Groq provides the fastest inference latency available for 
open-weight models. llama-3.3-70b-versatile has strong tool calling capability 
comparable to GPT-3.5-turbo at zero cost for prototyping.

**Tradeoff:** Free tier has a 100k tokens/day limit. Smaller models 
(llama-3.1-8b-instant) are unreliable for multi-step tool calling. Mitigated 
by using the 70b model as default.

---

### 3. ChromaDB over FAISS for RAG

**Decision:** Use ChromaDB as the vector store.

**Justification:** ChromaDB persists to disk out of the box, requires no 
serialisation logic, and integrates natively with LangChain. FAISS requires 
manual index saving and loading which adds operational complexity.

**Tradeoff:** ChromaDB is slower than FAISS for large corpora. Acceptable 
for this use case where the knowledge base is small (FAQs and policy docs).

---

### 4. SQLite for all persistence

**Decision:** Use SQLite for pricing data, session memory, long-term memory, 
and feedback — all in one file.

**Justification:** Zero infrastructure overhead. The agent is designed for 
local or single-instance deployment. SQLite handles concurrent reads well 
and is fully portable.

**Tradeoff:** Not suitable for multi-instance or high-concurrency deployments. 
A production upgrade path would replace SQLite with PostgreSQL.

---

### 5. HuggingFace all-MiniLM-L6-v2 for embeddings

**Decision:** Use a local embedding model instead of an API-based one.

**Justification:** No API cost, no latency overhead for embedding calls, and 
no dependency on external availability. all-MiniLM-L6-v2 is well-tested for 
semantic search on short documents.

**Tradeoff:** Lower embedding quality than text-embedding-3-large. Acceptable 
for FAQ-style retrieval where documents are short and queries are specific.

---

### 6. Prompt variant strategy (v1/v2/v3)

**Decision:** Maintain three prompt variants with a default selection.

**Justification:** Phase 3 required demonstrating prompt engineering impact. 
Three variants — minimal, structured, and default — were tested on the same 
query set to measure output quality differences.

**Selected default:** v3 (DEFAULT_PROMPT) — most explicit about tool usage, 
safety constraints, and response format. Produces the most consistent outputs 
across query types.

---

### 7. Feedback-driven adaptation

**Decision:** Store negative feedback and inject adaptation notes into the 
system prompt on subsequent queries.

**Justification:** Simple, explainable adaptation without fine-tuning. The 
agent can adjust its verbosity and completeness based on real user signals 
without retraining.

**Tradeoff:** Adaptation is prompt-level only — it does not update model 
weights or tool logic. A production system would route persistent failure 
patterns to a model improvement pipeline.

---

## Safety Approach

Safety is treated as a first-class feature, not an afterthought:

| Risk | Mitigation |
|---|---|
| Data modification requests | Agent has no write tools — refusal is structural |
| Policy fabrication | RAG retrieves only from verified knowledge base |
| Infinite loops | Recursion limit + graceful fallback message |
| PII in logs | Logs contain session IDs and message lengths only |
| Unresolved issues | escalate_to_developer tool triggers on anomalies |
| LLM hallucination | Tool outputs are database-sourced, not LLM-generated |

---

## Deployment Assumptions

- Single-instance local or cloud deployment
- Groq API available and quota sufficient
- ChromaDB index pre-built before startup
- SQLite database