# Deployment Guide

## Running Locally

### Prerequisites
- Python 3.12+
- uv package manager
- Groq API key

### Setup
```bash
git clone https://github.com/arikh/retail-ai-support-agent
cd retail-ai-support-agent
uv sync
cp .env.example .env
# Add your GROQ_API_KEY to .env
```

### Run CLI Agent
```bash
uv run python -m agent.llm_agent
```

### Run API Server
```bash
uv run uvicorn api.main:app --reload --port 8000
```

## API Endpoints

| Endpoint | Method | Description |
|---|---|---|
| /health | GET | Health check |
| /chat | POST | Send message to agent |
| /feedback | POST | Submit interaction feedback |

## Deployment Assumptions & Limitations

- Designed for local or single-instance cloud deployment
- No authentication layer (add API key middleware for production)
- Session memory is in-memory — resets on server restart
- Groq free tier has 100k TPD token limit
- ChromaDB is file-based — not suitable for multi-instance deployment

## Environment Variables

| Variable | Description | Default |
|---|---|---|
| GROQ_API_KEY | Groq API key | Required |
| LLM_MODEL | Model name | llama-3.3-70b-versatile |
| MAX_ITERATIONS | Agent loop limit | 15 |