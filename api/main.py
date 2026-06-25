"""
Phase 8: FastAPI deployment readiness.
Exposes the retail AI support agent as a REST API.
Includes latency tracking, error handling, and PII-safe logging.
"""

import uuid
import time
import logging
import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from api.schemas import (
    ChatRequest,
    ChatResponse,
    FeedbackRequest,
    FeedbackResponse,
    HealthResponse,
)
from agent.llm_agent import run_llm_agent
from agent.feedback.feedback_store import FeedbackStore
from agent.memory.session_memory import SessionMemory

load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Retail AI Support Agent",
    description="AI-powered pricing operations support agent.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── In-memory session store ───────────────────────────────────────────────────

sessions: dict[str, SessionMemory] = {}


def get_or_create_session(session_id: str) -> SessionMemory:
    if session_id not in sessions:
        sessions[session_id] = SessionMemory(session_id=session_id)
    return sessions[session_id]


# ── Routes ────────────────────────────────────────────────────────────────────

@app.get("/health", response_model=HealthResponse)
def health_check():
    """Health check endpoint."""
    return HealthResponse(
        status="ok",
        model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
        version="1.0.0",
    )


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    """
    Main chat endpoint.
    Accepts a user message and returns agent response.
    Maintains session memory across turns.
    """
    session_id = request.session_id or str(uuid.uuid4())[:8]
    memory     = get_or_create_session(session_id)

    logger.info(
        f"CHAT REQUEST | Session: {session_id} | "
        f"Variant: {request.prompt_variant} | "
        f"Message length: {len(request.message)} chars"
    )

    # Add user message to memory
    memory.add_user_message(request.message)

    # Get recent history excluding current message
    history        = memory.get_history()[:-1]
    recent_history = history[-6:] if len(history) > 6 else history

    # Track latency
    start_time = time.time()

    try:
        response = run_llm_agent(
            user_input     = request.message,
            prompt_variant = request.prompt_variant,
            chat_history   = recent_history,
        )
    except Exception as e:
        logger.error(f"CHAT ERROR | Session: {session_id} | Error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Agent failed to process request. Please try again."
        )

    latency_ms = round((time.time() - start_time) * 1000, 2)

    # Add response to memory
    memory.add_ai_message(response)

    logger.info(
        f"CHAT RESPONSE | Session: {session_id} | "
        f"Latency: {latency_ms}ms"
    )

    return ChatResponse(
        response   = response,
        session_id = session_id,
        latency_ms = latency_ms,
    )


@app.post("/feedback", response_model=FeedbackResponse)
def submit_feedback(request: FeedbackRequest):
    """
    Feedback endpoint.
    Stores interaction feedback for adaptive behaviour.
    """
    try:
        FeedbackStore().store(
            session_id     = request.session_id,
            user_query     = request.user_query,
            agent_response = request.agent_response,
            rating         = request.rating,
            comment        = request.comment,
        )
        logger.info(
            f"FEEDBACK | Session: {request.session_id} | "
            f"Rating: {'positive' if request.rating == 1 else 'negative'}"
        )
        return FeedbackResponse(
            status  = "ok",
            message = "Feedback recorded successfully.",
        )
    except Exception as e:
        logger.error(f"FEEDBACK ERROR: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Failed to store feedback."
        )