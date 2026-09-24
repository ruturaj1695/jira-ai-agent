from __future__ import annotations

import json
from typing import Any, TypedDict

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage
from langgraph.graph import END, START, StateGraph
from langgraph.prebuilt import create_react_agent

from .analytics import blocker_analysis, bug_trend, sprint_velocity, team_load
from .config import get_settings
from .domain import Intent, JiraIssue
from .jira_client import JiraClient
from .llm import LLMService
from .rag import RAGService
from .tools import AGENT_TOOLS


class AgentState(TypedDict, total=False):
    query: str
    intent: Intent
    history: list[dict[str, str]]
    issues: list[dict[str, Any]]
    analysis: dict[str, Any]
    knowledge: list[dict[str, Any]]
    answer: str
    sources: list[str]
    error: str


AGENTIC_SYSTEM_PROMPT = """You are the RTB Jira reporting/insights agent for project {project_key}.

You can answer ANY question about this Jira project — counts, filters,
assignments, blockers, bug trends, velocity, team load, sprint status, or
process/definition questions — by using your tools. Do not guess at Jira
data; always call jira_search (and calculate_sprint_metrics for aggregation
questions) before answering anything about issues, counts, or people.
Use knowledge_search for conceptual/process/definition questions instead.

Rules:
- Never fabricate issue keys, counts, names, or statuses — every concrete
  fact in your answer must come from a tool result.
- jira_search only accepts the filter portion of JQL; project scope and
  ordering are added automatically and cannot be overridden.
- For "how many"/count questions, prefer the "total" field from jira_search
  over counting the (possibly paginated) "issues" list.
- "assigned to me" / "my issues" means assignee = currentUser().
- If a tool call fails or returns no data, say so plainly rather than
  inventing an answer.
- Answer concisely in natural language. Only mention JQL or tool names if
  the user asks how you got the answer.
"""


def _history_to_messages(history: list[dict[str, str]]) -> list[Any]:
    messages: list[Any] = []
    for turn in history:
        role, content = turn.get("role"), turn.get("content", "")
        if role == "user":
            messages.append(HumanMessage(content=content))
        elif role == "assistant":
            messages.append(AIMessage(content=content))
    return messages


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
    if any(word in q for word in ("bug trend", "bugs trend", "bug count", "defects")):
        return "bugs_trend"
    if "spillover" in q or "carried over" in q or "carry over" in q:
        return "spillover"
    if any(word in q for word in ("velocity", "story points", "throughput")):
        return "velocity"
    if any(word in q for word in ("report", "summary", "performance", "insights")):
        return "report"
    if any(word in q for word in ("issue", "ticket", "jira", "search", "find")):
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
    intent = llm_intent or classify_intent(state["query"])
    return {"intent": intent, "sources": []}


async def agentic_node(state: AgentState) -> AgentState:
    """Free-form path: let the LLM choose which tool(s) to call for any question.

    This replaces the fixed-intent pipeline entirely when a model is
    configured. It's the only node that can answer questions outside the
    small set of intents the deterministic fallback below understands.
    """
    settings = get_settings()
    llm = LLMService(settings)
    project_key = settings.jira_project_key or "the configured project"
    agent = create_react_agent(
        llm.chat_model(),
        tools=AGENT_TOOLS,
        prompt=AGENTIC_SYSTEM_PROMPT.format(project_key=project_key),
    )

    messages = _history_to_messages(state.get("history", [])) + [
        HumanMessage(content=state["query"])
    ]

    try:
        result = await agent.ainvoke({"messages": messages})
    except Exception as exc:  # noqa: BLE001 - fall back to the deterministic pipeline below.
        return {"error": str(exc)}

    result_messages = result.get("messages", [])
    answer = ""
    for message in reversed(result_messages):
        if isinstance(message, AIMessage) and message.content:
            answer = str(message.content)
            break

    sources: set[str] = set()
    issues: list[dict[str, Any]] = []
    jira_total: int | None = None
    for message in result_messages:
        if not isinstance(message, ToolMessage):
            continue
        if message.name == "jira_search":
            sources.add("Jira API" if JiraClient(settings).configured else "Demo Jira dataset")
            try:
                payload = json.loads(message.content)
                issues = payload.get("issues", issues)
                jira_total = payload.get("total", jira_total)
            except (json.JSONDecodeError, TypeError):
                pass
        elif message.name == "knowledge_search":
            sources.add("Knowledge base")
        elif message.name == "calculate_sprint_metrics":
            sources.add("Jira analytics")
        elif message.name == "current_sprint_name":
            sources.add("Jira API")

    return {
        "answer": answer or "I wasn't able to produce an answer from the available tools.",
        "intent": "agentic",
        "sources": sorted(sources) or ["LLM reasoning"],
        "issues": issues,
        "jira_total": jira_total if jira_total is not None else len(issues),
    }


def route_from_start(state: AgentState) -> str:
    """Use the free-form tool-calling agent whenever a model is configured.

    The fixed-intent pipeline (router -> data/knowledge -> analytics -> report)
    is kept only as the offline fallback for when no LLM is reachable — it can
    never cover arbitrary phrasing, only the deterministic path below can.
    """
    if LLMService(get_settings()).available():
        return "agentic"
    return "router"


def route_after_agentic(state: AgentState) -> str:
    # If the agentic path errored (e.g. transient model failure), degrade
    # gracefully to the deterministic pipeline instead of failing the request.
    return "router" if state.get("error") else END


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
            "total_issues": len(issues),
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
        issue_lines = "\n".join(
            f"- {item['key']}: {item['summary']} | {item['status']} | {item['priority']}"
            for item in state.get("issues", [])
        )
        answer = (
            f"I retrieved {len(state.get('issues', []))} Jira issue(s) from the configured project.\n"
            f"{issue_lines or 'No matching Jira issues found.'}"
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
    graph.add_node("agentic", agentic_node)
    graph.add_node("router", router_node)
    graph.add_node("data", data_agent_node)
    graph.add_node("knowledge", knowledge_agent_node)
    graph.add_node("analytics", analytics_agent_node)
    graph.add_node("report", report_agent_node)

    graph.add_conditional_edges(
        START,
        route_from_start,
        {"agentic": "agentic", "router": "router"},
    )
    graph.add_conditional_edges(
        "agentic",
        route_after_agentic,
        {"router": "router", END: END},
    )
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
