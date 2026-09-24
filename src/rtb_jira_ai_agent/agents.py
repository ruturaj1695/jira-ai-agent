from __future__ import annotations

from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph

from .analytics import blocker_analysis, bug_trend, sprint_velocity, team_load
from .config import get_settings
from .domain import Intent, JiraIssue
from .jira_client import JiraClient
from .llm import LLMService
from .rag import RAGService


class AgentState(TypedDict, total=False):
    query: str
    intent: Intent
    history: list[dict[str, str]]
    issues: list[dict[str, Any]]
    jira_total: int
    analysis: dict[str, Any]
    knowledge: list[dict[str, Any]]
    answer: str
    sources: list[str]
    error: str


def classify_intent(query: str) -> Intent:
    """Deterministic fallback used when Ollama is unavailable."""
    q = query.lower()

    # Knowledge/definition requests take precedence over domain keywords. For example,
    # "What is sprint spillover?" is a knowledge request, not a spillover analysis request.
    if any(
        word in q
        for word in ("definition", "documentation", "document", "process", "policy", "what is")
    ):
        return "knowledge"
    if any(word in q for word in ("blocker", "blocked", "impediment", "risk")):
        return "blockers"
    if any(word in q for word in ("bug trend", "bugs trend", "bug count", "defects trend")):
        return "bugs_trend"
    if "spillover" in q or "carried over" in q or "carry over" in q:
        return "spillover"
    if any(word in q for word in ("velocity", "story points", "throughput")):
        return "velocity"
    if any(word in q for word in ("report", "summary", "performance", "insights")):
        return "report"
    if any(
        phrase in q
        for phrase in (
            "how many",
            "count",
            "issue",
            "issues",
            "ticket",
            "tickets",
            "jira",
            "search",
            "find",
            "show",
            "assigned to",
            "assigned",
            "my issues",
            "mine",
            "open",
            "unresolved",
            "created",
            "updated",
        )
    ):
        return "search"
    return "unknown"


def build_jql(query: str, intent: Intent, project_key: str | None) -> str:
    """Build conservative JQL; the LLM never gets unrestricted Jira execution rights."""
    project = project_key or "DEMO"
    clauses = [f'project = "{project}"']
    normalized = query.lower()

    if intent == "blockers":
        clauses.append('status = "Blocked"')
    elif intent == "bugs_trend":
        clauses.append('issuetype = "Bug"')
    elif "high priority" in normalized:
        clauses.append('priority = "High"')

    return " AND ".join(clauses) + " ORDER BY updated DESC"


async def router_node(state: AgentState) -> AgentState:
    settings = get_settings()
    llm = LLMService(settings)
    llm_intent = await llm.classify_intent(state["query"])
    fallback_intent = classify_intent(state["query"])
    # Treat an LLM "unknown" result as non-authoritative so common Jira query
    # patterns such as counts, assignments, filters, and lists still route to search.
    intent = fallback_intent if llm_intent in (None, "unknown") else llm_intent
    return {"intent": intent, "sources": []}


async def data_agent_node(state: AgentState) -> AgentState:
    settings = get_settings()
    client = JiraClient(settings)
    llm = LLMService(settings)

    # Prefer real natural-language-to-JQL translation when Ollama is configured.
    # The deterministic builder remains a safe fallback for offline/demo mode.
    jql = await llm.generate_jql(
        state["query"],
        settings.jira_project_key,
        history=state.get("history", []),
    )
    if not jql:
        jql = build_jql(state["query"], state["intent"], settings.jira_project_key)

    result = await client.search(jql)
    return {
        "issues": [issue.model_dump() for issue in result.issues],
        "jira_total": result.total,
        "sources": ["Jira API" if client.configured else "Demo Jira dataset"],
    }


def knowledge_agent_node(state: AgentState) -> AgentState:
    service = RAGService()
    try:
        results = service.search(state["query"], k=4)
    except Exception as exc:  # noqa: BLE001 - RAG is an optional dependency/fallback path.
        return {"knowledge": [], "sources": [], "error": str(exc)}

    sources = [item.get("metadata", {}).get("source", "knowledge base") for item in results]
    return {"knowledge": results, "sources": sources}


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
        analysis = {"historical_sprints": sprint_velocity(issues)}
    elif intent in {"search", "report", "unknown"}:
        analysis = {
            "total_issues": state.get("jira_total", len(issues)),
            "returned_issue_count": len(issues),
            "team_load": team_load(issues),
            "issues": [issue.model_dump() for issue in issues],
        }
    else:
        analysis = {"team_load": team_load(issues), "total_issues": len(issues)}
    return {"analysis": analysis}


async def report_agent_node(state: AgentState) -> AgentState:
    intent = state["intent"]
    analysis = state.get("analysis", {})
    knowledge = state.get("knowledge", [])

    if intent == "knowledge":
        analysis = {
            "knowledge": [
                {
                    "content": item["content"],
                    "source": item.get("metadata", {}).get("source"),
                }
                for item in knowledge
            ]
        }

    llm = LLMService(get_settings())
    generated = await llm.format_report(
        state["query"],
        analysis,
        history=state.get("history", []),
    )
    if generated:
        return {"answer": generated}

    if intent == "knowledge":
        if not knowledge:
            answer = (
                "No matching knowledge-base documents were found. "
                "Ingest the relevant RTB/Jira documentation first."
            )
        else:
            excerpts = "\n".join(f"- {item['content'][:500]}" for item in knowledge)
            answer = f"Relevant knowledge-base context:\n{excerpts}"
    elif intent == "blockers":
        blockers = analysis.get("count", 0)
        high = ", ".join(analysis.get("high_priority", [])) or "none"
        answer = (
            f"Current sprint blocker analysis: {blockers} blocker(s). "
            f"High-priority blockers: {high}."
        )
    elif intent == "bugs_trend":
        answer = f"Bug trend by sprint: {analysis.get('trend', {})}."
    elif intent == "velocity":
        answer = f"Completed story-point velocity by sprint: {analysis.get('velocity', {})}."
    elif intent == "spillover":
        answer = (
            "Spillover analysis requires committed and completed story-point history. "
            f"Available sprint metrics: {analysis.get('historical_sprints', {})}."
        )
    elif intent == "search":
        total = analysis.get("total_issues", len(state.get("issues", [])))
        query_lower = state["query"].lower()
        if "how many" in query_lower or "count" in query_lower:
            answer = f"I found {total} matching Jira issue(s) in the configured project."
        else:
            issue_lines = "\n".join(
                f"- {item['key']}: {item['summary']} | {item['status']} | {item['priority']}"
                for item in state.get("issues", [])
            )
            answer = (
                f"I retrieved {total} matching Jira issue(s) from the configured project.\n"
                f"{issue_lines or 'No matching Jira issues found in the returned page.'}"
            )
    elif intent == "report":
        answer = f"Jira report summary: {analysis}."
    else:
        answer = (
            "I can analyze Jira blockers, bug trends, spillover, velocity, "
            "team performance, reports, and knowledge-base questions."
        )
    return {"answer": answer}


def route_after_router(state: AgentState) -> str:
    return "knowledge" if state["intent"] == "knowledge" else "data"


def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("router", router_node)
    graph.add_node("data", data_agent_node)
    graph.add_node("knowledge", knowledge_agent_node)
    graph.add_node("analytics", analytics_agent_node)
    graph.add_node("report", report_agent_node)

    graph.add_edge(START, "router")
    graph.add_conditional_edges(
        "router",
        route_after_router,
        {"knowledge": "knowledge", "data": "data"},
    )
    graph.add_edge("knowledge", "report")
    graph.add_edge("data", "analytics")
    graph.add_edge("analytics", "report")
    graph.add_edge("report", END)
    return graph.compile()


agent_graph = build_graph()
