"""
Phase 3: LangChain + Groq powered agent using LangGraph.
Replaces brittle keyword matching with LLM-based understanding.
Compatible with LangChain 1.x / LangGraph.
"""
import sys
import sqlite3
import logging
import os
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.tools import tool
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langgraph.prebuilt import create_react_agent
from agent.feedback.feedback_store import FeedbackStore

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from agent.prompts.system_prompt import (
    DEFAULT_PROMPT,
    PROMPT_V1_MINIMAL,
    PROMPT_V2_STRUCTURED,
)


load_dotenv()

# ── Logging ───────────────────────────────────────────────────────────────────

logger = logging.getLogger(__name__)

# ── Database helper ───────────────────────────────────────────────────────────

DATABASE_PATH = "data/pricing.db"


def query_db(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a read-only query and return results as list of dicts."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        return [dict(row) for row in cursor.fetchall()]
    finally:
        conn.close()


# ── Tools ─────────────────────────────────────────────────────────────────────

@tool
def get_plan_status(plan_name: str) -> str:
    """
    Get the overall status of a pricing plan including how many
    materials were priced vs total selected.
    Use this when user asks about plan completeness or status.
    """
    rows = query_db("""
        SELECT plan_name, region, market, channel, season,
               status, total_materials, priced_materials
        FROM pricing_plans
        WHERE plan_name = ?
    """, (plan_name,))

    if not rows:
        return f"Plan '{plan_name}' not found. Please verify the plan name."

    r = rows[0]
    missing = r["total_materials"] - r["priced_materials"]
    return (
        f"Plan: {r['plan_name']} | Region: {r['region']} | "
        f"Market: {r['market']} | Channel: {r['channel']} | "
        f"Season: {r['season']} | Status: {r['status']} | "
        f"Materials priced: {r['priced_materials']}/{r['total_materials']} | "
        f"Missing: {missing}"
    )


@tool
def get_missing_materials(plan_name: str) -> str:
    """
    Get all materials that were selected in a plan but were NOT priced,
    along with the rejection reason for each.
    Use this when user asks why materials are missing or not showing up.
    """
    rows = query_db("""
        SELECT pm.material_id, m.material_name,
               pm.rejection_reason, m.expiry_months
        FROM plan_materials pm
        JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
        JOIN materials m ON pm.material_id = m.material_id
        WHERE pp.plan_name = ?
        AND pm.price_status = 'NOT_PRICED'
    """, (plan_name,))

    if not rows:
        return f"No missing materials found for plan '{plan_name}'."

    result = f"Missing materials in '{plan_name}':\n"
    for r in rows:
        result += (
            f"- {r['material_id']} ({r['material_name']}) | "
            f"Reason: {r['rejection_reason']} | "
            f"Expiry: {r['expiry_months']} months\n"
        )
    return result


@tool
def get_downstream_status(plan_name: str) -> str:
    """
    Get the downstream propagation status for all priced materials in a plan.
    Use this when user asks if prices were sent to client systems or downstreamed.
    """
    rows = query_db("""
        SELECT pm.material_id, m.material_name, pm.downstream_status
        FROM plan_materials pm
        JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
        JOIN materials m ON pm.material_id = m.material_id
        WHERE pp.plan_name = ?
        AND pm.price_status = 'PRICED'
    """, (plan_name,))

    if not rows:
        return f"No priced materials found for plan '{plan_name}'."

    failed  = [r for r in rows if r["downstream_status"] == "FAILED"]
    pending = [r for r in rows if r["downstream_status"] == "PENDING"]
    success = [r for r in rows if r["downstream_status"] == "DOWNSTREAMED"]

    result = (
        f"Downstream status for '{plan_name}':\n"
        f"Downstreamed: {len(success)} | "
        f"Pending: {len(pending)} | "
        f"Failed: {len(failed)}\n"
    )

    if failed:
        result += "Failed materials:\n"
        for r in failed:
            result += f"- {r['material_id']} ({r['material_name']})\n"

    return result


@tool
def get_material_rejection_reason(material_id: str, plan_name: str = "") -> str:
    """
    Get the rejection reason for a specific material in a plan.
    Use this when user asks why a specific material was not priced
    or what rule caused a material to be excluded.
    """
    if plan_name:
        rows = query_db("""
            SELECT pm.material_id, m.material_name,
                   pm.price_status, pm.rejection_reason,
                   m.expiry_months, pp.plan_name
            FROM plan_materials pm
            JOIN materials m ON pm.material_id = m.material_id
            JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
            WHERE pm.material_id = ? AND pp.plan_name = ?
        """, (material_id, plan_name))
    else:
        rows = query_db("""
            SELECT pm.material_id, m.material_name,
                   pm.price_status, pm.rejection_reason,
                   m.expiry_months, pp.plan_name
            FROM plan_materials pm
            JOIN materials m ON pm.material_id = m.material_id
            JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
            WHERE pm.material_id = ?
        """, (material_id,))

    if not rows:
        return f"Material '{material_id}' not found."

    r = rows[0]
    if r["price_status"] == "PRICED":
        return (
            f"Material {material_id} ({r['material_name']}) was successfully "
            f"priced in plan '{r['plan_name']}'."
        )

    return (
        f"Material {material_id} ({r['material_name']}) was NOT priced.\n"
        f"Plan: {r['plan_name']} | "
        f"Reason: {r['rejection_reason']} | "
        f"Expiry: {r['expiry_months']} months"
    )


@tool
def escalate_to_developer(
    plan_name: str,
    material_id: str,
    issue_description: str
) -> str:
    """
    Escalate an unresolved issue to a developer.
    Use this when root cause is unknown, data is inconsistent,
    or a system anomaly is detected.
    """
    logger.warning(
        f"ESCALATION TRIGGERED | "
        f"Plan: {plan_name} | "
        f"Material: {material_id} | "
        f"Issue: {issue_description}"
    )
    return (
        f"Escalation logged for developer review.\n"
        f"Plan: {plan_name} | Material: {material_id}\n"
        f"Issue: {issue_description}\n"
        f"A developer will investigate the system logs and database records."
    )

@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the pricing operations knowledge base for policy information,
    rule explanations, and resolution guidance.
    Use this when user asks about what a rule means, how to fix an issue,
    or what a status means. Do NOT use for live plan or material data.
    """
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from rag.retriever import retrieve_as_text

    result = retrieve_as_text(query)
    logger.info(f"RAG retrieved context for query: {query}")
    return result

# ── Tools list ────────────────────────────────────────────────────────────────

TOOLS = [
    get_plan_status,
    get_missing_materials,
    get_downstream_status,
    get_material_rejection_reason,
    escalate_to_developer,
    search_knowledge_base,
]


# ── Agent builder ─────────────────────────────────────────────────────────────

def build_agent(system_prompt: str):
    """
    Build and return a LangGraph ReAct agent with safeguards.
    - max_iterations prevents infinite tool loops
    - handle_parsing_errors prevents crashes on malformed LLM output
    """

    llm = ChatGroq(
        model=os.getenv("LLM_MODEL", "llama-3.3-70b-versatile"),
        api_key=os.getenv("GROQ_API_KEY"),
        temperature=0,
    )

    agent = create_react_agent(
        model=llm,
        tools=TOOLS,
        prompt=system_prompt,
    )

    return agent


def run_with_safeguards(agent, messages: list, max_iterations: int = 10) -> str:
    """
    Run agent with explicit safeguards:
    - Max iteration limit prevents infinite loops
    - Exception handling prevents crashes
    - Graceful fallback message on failure
    """
    try:
        result = agent.invoke(
            {"messages": messages},
            config={"recursion_limit": max_iterations}
        )
        return result["messages"][-1].content

    except Exception as e:
        error_msg = str(e)

        # Loop detection
        if "recursion" in error_msg.lower() or "iteration" in error_msg.lower():
            logger.error(f"LOOP DETECTED — agent exceeded {max_iterations} iterations")
            return (
                "I was unable to complete this request — it required too many "
                "steps to resolve. This has been logged. Please contact a developer "
                "with your plan name and material ID for manual investigation."
            )

        # General failure
        logger.error(f"AGENT ERROR: {error_msg}")
        return (
            "I encountered an unexpected error processing your request. "
            "Please try again or contact support if the issue persists."
        )


# ── Run with prompt variant ───────────────────────────────────────────────────

def run_llm_agent(
    user_input: str,
    prompt_variant: str = "v3",
    chat_history: list = None
) -> str:
    """
    Run the LLM agent with a specific prompt variant.
    Accepts optional chat history for multi-turn conversations.
    """
    prompt_map = {
        "v1": PROMPT_V1_MINIMAL,
        "v2": PROMPT_V2_STRUCTURED,
        "v3": DEFAULT_PROMPT,
    }

    
    # Add feedback loop
    feedback_store  = FeedbackStore()
    adaptation      = feedback_store.build_adaptation_context()
    system_prompt   = prompt_map.get(prompt_variant, DEFAULT_PROMPT) + adaptation
    agent           = build_agent(system_prompt)

    logger.info(
        f"LLM AGENT | Prompt: {prompt_variant} | Input: {user_input}"
    )

    messages = []
    if chat_history:
        messages.extend(chat_history)
    messages.append(HumanMessage(content=user_input))

    max_iter = int(os.getenv("MAX_ITERATIONS", 15))
    response = run_with_safeguards(agent, messages, max_iter)
    logger.info(f"LLM AGENT RESPONSE: {response}")
    return response


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    """
    Interactive CLI with session memory.
    Demonstrates multi-turn conversation capability.
    """
    import uuid
    from agent.memory.session_memory import SessionMemory

    print("=" * 60)
    print("  Retail Pricing Operations — AI Support Agent")
    print("  Phase 6: Memory + Multi-turn Conversations")
    print("=" * 60)
    print("Commands:")
    print("  'v1', 'v2', 'v3'  — switch prompt variant")
    print("  'clear'           — clear session memory")
    print("  'memory'          — show memory state")
    print("  'quit'            — exit")
    print()

    session_id      = str(uuid.uuid4())[:8]
    memory          = SessionMemory(session_id=session_id)
    current_variant = "v3"

    print(f"Session ID: {session_id}")
    print(f"Active prompt variant: {current_variant}\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye.")
            logger.info(f"Session {session_id} ended by user.")
            break

        if user_input.lower() in ["v1", "v2", "v3"]:
            current_variant = user_input.lower()
            print(f"Switched to prompt variant: {current_variant}\n")
            continue

        if user_input.lower() == "clear":
            memory.clear_session()
            print("Session memory cleared.\n")
            continue

        if user_input.lower() == "memory":
            print(f"Memory state: {memory.get_memory_summary()}\n")
            continue

        # Add user message to memory
        memory.add_user_message(user_input)

        # Run agent with limited history — last 2 turns only
        # Prevents loop from re-investigating previous tool results
        history = memory.get_history()[:-1]
        recent_history = history[-4:] if len(history) > 4 else history

        response = run_llm_agent(
            user_input     = user_input,
            prompt_variant = current_variant,
            chat_history   = recent_history,
        )

        # Add agent response to memory
        memory.add_ai_message(response)

        # Store key entities in long-term memory
        import re
        plan_match     = re.search(r'\b([A-Z][A-Z0-9_]{5,})\b', user_input)
        material_match = re.search(r'\bM-\d{4}\b', user_input)
        if plan_match:
            memory.remember("last_plan", plan_match.group())
        if material_match:
            memory.remember("last_material", material_match.group())

        
        print(f"\nAgent: {response}\n")

        # Collect feedback
        feedback_input = input("Feedback? [y/n/skip]: ").strip().lower()
        if feedback_input in ["y", "n"]:
            rating  = 1 if feedback_input == "y" else 0
            comment = input("Comment (optional, press Enter to skip): ").strip()
            from agent.feedback.feedback_store import FeedbackStore
            FeedbackStore().store(
                session_id     = session_id,
                user_query     = user_input,
                agent_response = response,
                rating         = rating,
                comment        = comment,
            )
            print(f"Feedback recorded.\n")
        print("-" * 60)


if __name__ == "__main__":
    main()