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