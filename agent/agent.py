"""
Phase 2: Baseline Rule-Based Agent
No LLM. Pure keyword matching and template responses.
Deliberately limited to demonstrate baseline shortcomings.
"""

import re
import json
import sqlite3
import logging
import os
from datetime import datetime

# ── Logging setup ────────────────────────────────────────────────────────────

os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    handlers=[logging.FileHandler("logs/agent.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────

DATABASE_PATH = "data/pricing.db"

UNSAFE_KEYWORDS = [
    "delete",
    "update",
    "modify",
    "change",
    "edit",
    "approve",
    "trigger",
    "run",
    "execute",
    "insert",
]

# ── Database helper ───────────────────────────────────────────────────────────


def query_db(sql: str, params: tuple = ()) -> list[dict]:
    """Execute a read-only query and return results as list of dicts."""
    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        conn.close()


# ── Safety check ──────────────────────────────────────────────────────────────


def is_unsafe_request(user_input: str) -> bool:
    """Check if user is asking agent to modify data."""
    lowered = user_input.lower()
    return any(keyword in lowered for keyword in UNSAFE_KEYWORDS)


# ── Intent detection ──────────────────────────────────────────────────────────


def detect_intent(user_input: str) -> str:
    """
    Detect user intent using keyword matching.
    Returns intent string.

    LIMITATION: Brittle keyword matching — fails on paraphrasing,
    typos, or questions that don't contain exact keywords.
    """
    lowered = user_input.lower()

    if any(w in lowered for w in ["missing", "not showing", "excluded", "where are"]):
        return "missing_materials"

    if any(
        w in lowered for w in ["downstream", "propagated", "sent to client", "failed"]
    ):
        return "downstream_status"

    if any(w in lowered for w in ["why", "reason", "rule", "rejected"]):
        return "rejection_reason"

    if any(w in lowered for w in ["status", "complete", "progress", "how many"]):
        return "plan_status"

    return "unknown"


# ── Entity extraction ─────────────────────────────────────────────────────────


def extract_plan_name(user_input: str) -> str | None:
    """
    Extract plan name from user input using regex.
    Looks for patterns like SUMMER_LATAM_V2 or FALL_EU_2024.

    LIMITATION: Only works if user types exact plan name.
    Cannot handle 'my summer plan' or 'the LATAM plan'.
    """
    pattern = r"\b([A-Z][A-Z0-9_]{3,})\b"
    matches = re.findall(pattern, user_input)
    if matches:
        return matches[0]
    return None


def extract_material_id(user_input: str) -> str | None:
    """
    Extract material ID from user input.
    Looks for patterns like M-1001 or M-2001.

    LIMITATION: Only works with exact M-XXXX format.
    """
    pattern = r"\bM-\d{4}\b"
    match = re.search(pattern, user_input)
    if match:
        return match.group()
    return None


# ── Response handlers ─────────────────────────────────────────────────────────


def handle_missing_materials(plan_name: str) -> str:
    """Query and return missing materials for a plan."""
    rows = query_db(
        """
        SELECT pm.material_id, pm.rejection_reason, m.material_name
        FROM plan_materials pm
        JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
        JOIN materials m ON pm.material_id = m.material_id
        WHERE pp.plan_name = ?
        AND pm.price_status = 'NOT_PRICED'
    """,
        (plan_name,),
    )

    if not rows:
        return (
            f"No missing materials found for plan '{plan_name}'. "
            f"All selected materials were priced successfully. "
            f"If this seems incorrect, please verify the plan name and try again."
        )

    lines = [f"Missing materials in plan '{plan_name}':\n"]
    for row in rows:
        reason = row["rejection_reason"] or "Unknown"
        lines.append(
            f"  • {row['material_id']} ({row['material_name']}) — Reason: {reason}"
        )

    lines.append(
        "\nNote: EXPIRY_HORIZON_RULE means the material expiry is shorter "
        "than the plan pricing horizon. ACTIVE_MATERIAL_RULE means the "
        "material is inactive or discontinued."
    )
    return "\n".join(lines)


def handle_downstream_status(plan_name: str) -> str:
    """Query and return downstream status for a plan."""
    rows = query_db(
        """
        SELECT pm.material_id, pm.downstream_status, m.material_name
        FROM plan_materials pm
        JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
        JOIN materials m ON pm.material_id = m.material_id
        WHERE pp.plan_name = ?
        AND pm.price_status = 'PRICED'
    """,
        (plan_name,),
    )

    if not rows:
        return f"No priced materials found for plan '{plan_name}'."

    failed = [r for r in rows if r["downstream_status"] == "FAILED"]
    pending = [r for r in rows if r["downstream_status"] == "PENDING"]
    success = [r for r in rows if r["downstream_status"] == "DOWNSTREAMED"]

    lines = [f"Downstream status for plan '{plan_name}':\n"]
    lines.append(f"  ✓ Successfully downstreamed: {len(success)}")
    lines.append(f"  ⏳ Pending:                  {len(pending)}")
    lines.append(f"  ✗ Failed:                   {len(failed)}")

    if failed:
        lines.append("\nFailed materials (escalation recommended):")
        for r in failed:
            lines.append(f"  • {r['material_id']} ({r['material_name']})")

    return "\n".join(lines)


def handle_plan_status(plan_name: str) -> str:
    """Query and return overall plan status."""
    rows = query_db(
        """
        SELECT plan_name, region, market, channel, season,
               status, total_materials, priced_materials
        FROM pricing_plans
        WHERE plan_name = ?
    """,
        (plan_name,),
    )

    if not rows:
        return (
            f"Plan '{plan_name}' not found in the system. "
            f"Please check the plan name and try again."
        )

    r = rows[0]
    missing = r["total_materials"] - r["priced_materials"]

    return (
        f"Plan Status: {r['plan_name']}\n"
        f"  Region:    {r['region']} — {r['market']}\n"
        f"  Channel:   {r['channel']}\n"
        f"  Season:    {r['season']}\n"
        f"  Status:    {r['status']}\n"
        f"  Materials: {r['priced_materials']}/{r['total_materials']} priced"
        + (f"\n  Missing:   {missing} materials not priced" if missing > 0 else "")
    )


def handle_rejection_reason(material_id: str, plan_name: str | None) -> str:
    """Query rejection reason for a specific material."""
    if plan_name:
        rows = query_db(
            """
            SELECT pm.rejection_reason, pm.price_status,
                   m.material_name, m.expiry_months,
                   pp.plan_name
            FROM plan_materials pm
            JOIN materials m ON pm.material_id = m.material_id
            JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
            WHERE pm.material_id = ?
            AND pp.plan_name = ?
        """,
            (material_id, plan_name),
        )
    else:
        rows = query_db(
            """
            SELECT pm.rejection_reason, pm.price_status,
                   m.material_name, m.expiry_months,
                   pp.plan_name
            FROM plan_materials pm
            JOIN materials m ON pm.material_id = m.material_id
            JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
            WHERE pm.material_id = ?
        """,
            (material_id,),
        )

    if not rows:
        return f"Material '{material_id}' not found. Please verify the material ID."

    r = rows[0]
    if r["price_status"] == "PRICED":
        return (
            f"Material {material_id} ({r['material_name']}) was successfully "
            f"priced in plan '{r['plan_name']}'. No rejection recorded."
        )

    reason = r["rejection_reason"] or "Unknown — escalation recommended"
    return (
        f"Material {material_id} ({r['material_name']}) was NOT priced.\n"
        f"  Plan:            {r['plan_name']}\n"
        f"  Rejection Reason: {reason}\n"
        f"  Expiry Months:   {r['expiry_months']}"
    )


# ── Safety refusal ────────────────────────────────────────────────────────────


def handle_unsafe_request() -> str:
    """Return safety refusal message."""
    return (
        "I'm sorry, I cannot perform that action. "
        "This agent is read-only and cannot modify, delete, approve, "
        "or trigger any actions in the system. "
        "Please contact your system administrator for data modifications."
    )


# ── Unknown intent ────────────────────────────────────────────────────────────


def handle_unknown() -> str:
    """Return fallback message for unrecognised intent."""
    return (
        "I didn't understand your request. I can help you with:\n"
        "  • Missing materials in a pricing plan\n"
        "  • Downstream status of a plan\n"
        "  • Why a specific material was not priced\n"
        "  • Overall plan status\n\n"
        "Please include the plan name (e.g. SUMMER_LATAM_V2) "
        "or material ID (e.g. M-1001) in your question."
    )


# ── Main agent function ───────────────────────────────────────────────────────


def run_agent(user_input: str) -> str:
    """
    Main agent entry point.
    Takes user input, detects intent, queries database, returns response.
    """
    logger.info(f"USER INPUT: {user_input}")

    # Safety check first
    if is_unsafe_request(user_input):
        response = handle_unsafe_request()
        logger.warning(f"UNSAFE REQUEST blocked: {user_input}")
        logger.info(f"AGENT RESPONSE: {response}")
        return response

    # Extract entities
    plan_name = extract_plan_name(user_input)
    material_id = extract_material_id(user_input)
    intent = detect_intent(user_input)

    logger.info(f"INTENT: {intent} | PLAN: {plan_name} | MATERIAL: {material_id}")

    # Route to handler
    if intent == "missing_materials" and plan_name:
        response = handle_missing_materials(plan_name)

    elif intent == "downstream_status" and plan_name:
        response = handle_downstream_status(plan_name)

    elif intent == "plan_status" and plan_name:
        response = handle_plan_status(plan_name)

    elif intent == "rejection_reason" and material_id:
        response = handle_rejection_reason(material_id, plan_name)

    elif plan_name and not intent == "unknown":
        # Have plan name but unclear intent — default to plan status
        response = handle_plan_status(plan_name)

    else:
        response = handle_unknown()

    logger.info(f"AGENT RESPONSE: {response}\n")
    return response


# ── CLI loop ──────────────────────────────────────────────────────────────────


def main():
    """Interactive CLI for testing the baseline agent."""
    print("=" * 60)
    print("  Retail Pricing Operations — AI Support Agent")
    print("  Phase 2: Baseline Rule-Based Agent")
    print("=" * 60)
    print("Type 'quit' to exit\n")

    while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "q"]:
            print("Goodbye.")
            logger.info("Session ended by user.")
            break

        response = run_agent(user_input)
        print(f"\nAgent: {response}\n")
        print("-" * 60)


if __name__ == "__main__":
    main()
