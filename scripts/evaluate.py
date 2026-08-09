"""Offline evaluation harness for representative RTB demo queries."""

import asyncio
import time

from rtb_jira_ai_agent.agents import agent_graph


CASES = [
    ("What are blockers in current sprint?", "blockers"),
    ("Show bugs trend over last 3 sprints", "bugs_trend"),
    ("Show sprint velocity", "velocity"),
    ("Generate a team performance report", "report"),
    ("What is the role of the Router Agent?", "knowledge"),
]


async def main() -> None:
    passed = 0
    total_latency_ms = 0.0

    for query, expected_intent in CASES:
        started = time.perf_counter()
        result = await agent_graph.ainvoke({"query": query, "history": []})
        latency_ms = (time.perf_counter() - started) * 1000
        total_latency_ms += latency_ms
        ok = result.get("intent") == expected_intent and bool(result.get("answer"))
        passed += int(ok)
        print(
            f"{'PASS' if ok else 'FAIL'} | {query} | "
            f"intent={result.get('intent')} | latency_ms={latency_ms:.2f}"
        )

    accuracy = passed / len(CASES)
    average_latency = total_latency_ms / len(CASES)
    print(f"Accuracy: {passed}/{len(CASES)} = {accuracy:.0%}")
    print(f"Average latency: {average_latency:.2f} ms")


if __name__ == "__main__":
    asyncio.run(main())
