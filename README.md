# Retail AI Support Agent

Production-grade AI support agent for retail pricing operations — built with LangChain, LangGraph, Groq, ChromaDB, and FastAPI.

## Overview

An AI agent that assists pricing operations teams in resolving plan and material issues. It handles ambiguous queries, retrieves knowledge from a vector store, calls structured tools, maintains session memory, and enforces safety guardrails — all in a multi-turn conversational interface.

**Scenario:** Customer Support — AI Support Resolution Agent (Scenario 3)  
**Track:** Track A — LangChain + LangGraph

---

## Architecture

```
User Input
    │
    ▼
FastAPI /chat endpoint
    │
    ▼
Session Memory (short-term + long-term via SQLite)
    │
    ▼
LangGraph ReAct Agent
    │
    ├── get_plan_status
    ├── get_missing_materials
    ├── get_downstream_status
    ├── get_material_rejection_reason
    ├── escalate_to_developer
    └── search_knowledge_base (RAG → ChromaDB)
    │
    ▼
Feedback Store (adaptive behaviour)
    │
    ▼
Response
```

---

## Project Structure

```
retail-ai-support-agent/
├── agent/
│   ├── agent.py              # Phase 2: Rule-based baseline agent
│   ├── llm_agent.py          # Phase 3-6: LangGraph ReAct agent
│   ├── prompts/              # Phase 3: Prompt variants v1/v2/v3
│   ├── memory/               # Phase 6: Session memory manager
│   └── feedback/             # Phase 7: Adaptive feedback store
├── rag/                      # Phase 4: RAG pipeline
├── api/                      # Phase 8: FastAPI deployment
├── evaluation/               # Phase 9: Evaluation harness
├── data/
│   ├── pricing.db            # SQLite database
│   ├── faqs/                 # Knowledge base documents
│   └── setup_db.py
├── docs/
│   ├── deployment.md
│   ├── demo_script.md
│   ├── engineering_justification.md
│   └── evaluation_notes.txt
└── pyproject.toml
```

---

## Setup

### Prerequisites

- Python 3.12+
- uv package manager
- Groq API key (free tier at console.groq.com)

### Install

```bash
git clone https://github.com/arikh/retail-ai-support-agent
cd retail-ai-support-agent
uv sync
cp .env.example .env
# Add your GROQ_API_KEY to .env
```

### Setup database and knowledge base

```bash
uv run python -m data.setup_db
uv run python -m rag.ingest
```

---

## Running the Agent

### CLI (interactive multi-turn)

```bash
uv run python -m agent.llm_agent
```

### API Server

```bash
uv run uvicorn api.main:app --reload --port 8000
```

API docs available at: `http://localhost:8000/docs`

### Evaluation Harness

```bash
uv run python -m evaluation.evaluator
```

---

## Key Capabilities

| Capability | Implementation |
|---|---|
| LLM reasoning | LangGraph ReAct + Groq llama-3.3-70b-versatile |
| Knowledge retrieval | ChromaDB + HuggingFace all-MiniLM-L6-v2 |
| Tool calling | 5 structured tools with schemas |
| Session memory | Short-term (in-memory) + long-term (SQLite) |
| Adaptive behaviour | Feedback store + prompt injection |
| Safety enforcement | Refusals, escalation, PII-safe logging |
| Loop prevention | Recursion limit + graceful fallback |
| Deployment | FastAPI with latency tracking |

---

## Safety Design

- Refuses requests to modify data or trigger system actions
- Does not fabricate policies or pricing rules
- Escalates unresolved or anomalous cases to developers
- No personal data stored in logs — session IDs only
- Graceful failure handling on LLM errors

---

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| GROQ_API_KEY | Groq API key | Required |
| LLM_MODEL | Model name | llama-3.3-70b-versatile |
| MAX_ITERATIONS | Agent loop limit | 15 |

---

## Tech Stack

- **LangChain + LangGraph** — agent framework and ReAct loop
- **Groq** — LLM inference (llama-3.3-70b-versatile)
- **ChromaDB** — vector store for RAG
- **HuggingFace** — all-MiniLM-L6-v2 embeddings
- **SQLite** — structured data + memory + feedback persistence
- **FastAPI** — REST API deployment
- **uv** — dependency management