from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .analytics import blocker_analysis, bug_trend, sprint_velocity, team_load
from .config import get_settings
from .domain import Intent, JiraIssue
from .jira_client import JiraClient


class AgentState(TypedDict, total=False):
    query: str
    intent: Intent
    issues: list[dict[str, Any]]
    analysis: dict[str, Any]
    answer: str
    sources: list[str]
    error: str


def classify_intent(query: str) -> Intent:
    q = query.lower()
    if any(word in q for word in ("blocker", "blocked", "impediment", "risk")):
        return "blockers"
    if any(word in q for word in ("bug trend", "bugs trend", "bug count", "defects")):
        return "bugs_trend"
    if "spillover" in q:
        return "spillover"
    if any(word in q for word in ("velocity", "story points", "throughput")):
        return "velocity"
    if any(word in q for word in ("report", "summary", "performance", "insights")):
        return "report"
    if any(word in q for word in ("issue", "ticket", "jira", "search", "find")):
        return "search"
    return "unknown"


def router_node(state: AgentState) -> AgentState:
    return {"intent": classify_intent(state["query"]), "sources": []}


async def data_agent_node(state: AgentState) -> AgentState:
    client = JiraClient(get_settings())
    result = await client.search('project = "' + (get_settings().jira_project_key or "DEMO") + '"')
    return {
        "issues": [issue.model_dump() for issue in result.issues],
        "sources": ["Jira API" if client.configured else "Demo Jira dataset"],
    }


def analytics_agent_node(state: AgentState) -> AgentState:
    issues = [JiraIssue.model_validate(item) for item in state.get("issues", [])]
    intent = state["intent"]
    if intent == "blockers":
        analysis = blocker_analysis(issues)
    elif intent == "bugs_trend":
        analysis = {"trend": bug_trend(issues)}
    elif intent == "velocity":
        analysis = {"velocity": sprint_velocity(issues)}
    elif intent == "spillover":
        # A demo-friendly proxy: completed work from older sprints is treated as history.
        analysis = {"historical_sprints": sprint_velocity(issues)}
    else:
        analysis = {"team_load": team_load(issues), "total_issues": len(issues)}
    return {"analysis": analysis}


def report_agent_node(state: AgentState) -> AgentState:
    intent = state["intent"]
    analysis = state.get("analysis", {})
    if intent == "blockers":
        blockers = analysis.get("count", 0)
        high = ", ".join(analysis.get("high_priority", [])) or "none"
        answer = f"Current sprint blocker analysis: {blockers} blocker(s). High-priority blockers: {high}."
    elif intent == "bugs_trend":
        answer = f"Bug trend by sprint: {analysis.get('trend', {})}."
    elif intent == "velocity":
        answer = f"Completed story-point velocity by sprint: {analysis.get('velocity', {})}."
    elif intent == "spillover":
        answer = "Spillover analysis requires historical sprint commitment/completion data; the current adapter exposes the available sprint metrics."
    elif intent == "search":
        answer = f"I retrieved {len(state.get('issues', []))} Jira issue(s)."
    elif intent == "report":
        answer = f"Jira report summary: {analysis}."
    else:
        answer = "I can analyze Jira blockers, bug trends, spillover, velocity, team performance, and reports."
    return {"answer": answer}


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("data", data_agent_node)
    graph.add_node("analytics", analytics_agent_node)
    graph.add_node("report", report_agent_node)
    graph.add_edge(START, "router")
    graph.add_edge("router", "data")
    graph.add_edge("data", "analytics")
    graph.add_edge("analytics", "report")
    graph.add_edge("report", END)
    return graph.compile()


agent_graph = build_graph()
