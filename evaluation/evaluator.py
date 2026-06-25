"""
Phase 9: Evaluation harness.
Runs all test cases through the agent and scores responses.
Outputs a results table and saves to evaluation/results/.
"""

import json
import time
import logging
import os
import csv
from datetime import datetime
import time as time_module

sys_path_fix = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
import sys

sys.path.insert(0, sys_path_fix)

from agent.llm_agent import run_llm_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)

TEST_CASES_PATH = "evaluation/test_cases.json"
RESULTS_DIR = "evaluation/results"


def load_test_cases() -> list[dict]:
    """Load test cases from JSON file."""
    with open(TEST_CASES_PATH, "r") as f:
        data = json.load(f)
    return data["test_cases"]


def score_response(response: str, keywords: list[str]) -> tuple[bool, str]:
    """
    Score a response by checking for expected keywords.
    Returns (passed, reason).
    """
    response_lower = response.lower()
    matched = [kw for kw in keywords if kw.lower() in response_lower]
    failed = [kw for kw in keywords if kw.lower() not in response_lower]

    if len(matched) >= max(1, len(keywords) // 2):
        return True, f"Matched keywords: {matched}"
    else:
        return False, f"Missing keywords: {failed}"


def run_evaluation() -> list[dict]:
    """Run all test cases and return results."""
    test_cases = load_test_cases()
    results = []

    print("\n" + "=" * 70)
    print("  Retail AI Support Agent — Evaluation Harness")
    print(f"  Running {len(test_cases)} test cases")
    print("=" * 70 + "\n")

    for tc in test_cases:
        print(f"Running {tc['id']} — {tc['description']}...")

        time_module.sleep(10)  # avoid rate limiting between cases
        start_time = time.time()
        try:
            response = run_llm_agent(
                user_input=tc["input"],
                prompt_variant="v3",
            )
            error = None
        except Exception as e:
            response = ""
            error = str(e)
            logger.error(f"Test {tc['id']} failed with error: {error}")

        latency_ms = round((time.time() - start_time) * 1000, 2)
        passed, reason = score_response(response, tc["keywords"])

        result = {
            "id": tc["id"],
            "category": tc["category"],
            "description": tc["description"],
            "input": tc["input"],
            "response": response[:200] + "..." if len(response) > 200 else response,
            "passed": passed,
            "reason": reason,
            "latency_ms": latency_ms,
            "error": error or "",
        }

        results.append(result)
        status = "PASS" if passed else "FAIL"
        print(f"  {status} | {latency_ms}ms | {reason}\n")

    return results


def save_results(results: list[dict]) -> str:
    """Save results to CSV file."""
    os.makedirs(RESULTS_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filepath = f"{RESULTS_DIR}/eval_{timestamp}.csv"

    fieldnames = [
        "id",
        "category",
        "description",
        "input",
        "response",
        "passed",
        "reason",
        "latency_ms",
        "error",
    ]

    with open(filepath, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    logger.info(f"Results saved to {filepath}")
    return filepath


def print_summary(results: list[dict]) -> None:
    """Print evaluation summary table."""
    total = len(results)
    passed = sum(1 for r in results if r["passed"])
    failed = total - passed
    avg_lat = round(sum(r["latency_ms"] for r in results) / total, 2)

    print("\n" + "=" * 70)
    print("  EVALUATION SUMMARY")
    print("=" * 70)
    print(f"  Total:   {total}")
    print(f"  Passed:  {passed}")
    print(f"  Failed:  {failed}")
    print(f"  Score:   {passed}/{total} ({round(passed / total * 100)}%)")
    print(f"  Avg Latency: {avg_lat}ms")
    print("=" * 70)

    print("\n  RESULTS BY CATEGORY:")
    categories = {}
    for r in results:
        cat = r["category"]
        if cat not in categories:
            categories[cat] = {"pass": 0, "fail": 0}
        if r["passed"]:
            categories[cat]["pass"] += 1
        else:
            categories[cat]["fail"] += 1

    for cat, counts in categories.items():
        print(f"  {cat:<25} Pass: {counts['pass']} | Fail: {counts['fail']}")

    print("\n  FAILED CASES:")
    failed_cases = [r for r in results if not r["passed"]]
    if failed_cases:
        for r in failed_cases:
            print(f"  {r['id']} — {r['description']}")
            print(f"    Reason: {r['reason']}")
            print(f"    Response: {r['response'][:100]}...")
    else:
        print("  All cases passed.")
    print("=" * 70 + "\n")


def main():
    results = run_evaluation()
    filepath = save_results(results)
    print_summary(results)
    print(f"Full results saved to: {filepath}\n")


if __name__ == "__main__":
    main()
