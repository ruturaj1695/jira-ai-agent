"""Small offline evaluation harness for the RTB demo queries."""

import asyncio

from rtb_jira_ai_agent.agents import agent_graph


CASES = [
    ("What are blockers in current sprint?", "blockers"),
    ("Show bugs trend over last 3 sprints", "bugs_trend"),
    ("Show sprint velocity", "velocity"),
    ("Generate a team performance report", "report"),
]


async def main() -> None:
    passed = 0
    for query, expected_intent in CASES:
        result = await agent_graph.ainvoke({"query": query})
        ok = result.get("intent") == expected_intent and bool(result.get("answer"))
        passed += int(ok)
        print(f"{'PASS' if ok else 'FAIL'} | {query} | intent={result.get('intent')}")
    print(f"Accuracy: {passed}/{len(CASES)} = {passed / len(CASES):.0%}")


if __name__ == "__main__":
    asyncio.run(main())
