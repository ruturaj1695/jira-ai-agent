import json

from langchain_core.tools import tool

from .analytics import blocker_analysis, bug_trend, sprint_velocity, team_load
from .config import get_settings
from .jira_client import JiraClient
from .rag import RAGService


def scope_and_validate_jql(raw_jql: str, project_key: str) -> str:
    """Force project scope onto model-authored JQL and reject unsafe input.

    Mirrors the guardrails already applied to the deterministic fallback path
    (LLMService.generate_jql / build_jql): the model may express any filter it
    likes, but it never gets to choose the project or slip in write operations.
    """
    normalized = (raw_jql or "").strip()
    lowered = normalized.lower()
    if ";" in normalized:
        raise ValueError("jql must not contain statement separators")
    if "project" in lowered:
        raise ValueError(
            "jql must not set its own project clause; the project is fixed by the application"
        )
    if lowered.startswith("order by"):
        normalized = ""  # let the caller apply the default ordering only
    if not normalized:
        return f'project = "{project_key}" ORDER BY updated DESC'
    return f'project = "{project_key}" AND ({normalized}) ORDER BY updated DESC'


@tool
async def jira_search(jql: str) -> str:
    """Search Jira for issues matching a JQL filter expression.

    Pass only the filter portion of the query (e.g. 'issuetype = "Bug" AND
    assignee = currentUser()') — do NOT include a project clause or ORDER BY;
    those are added automatically and scoped to the configured project.
    Useful JQL building blocks: assignee = currentUser(), issuetype = "Bug",
    status = "Blocked", statusCategory != "Done", resolution IS EMPTY,
    sprint in openSprints(), priority = "High", created >= -7d.
    Returns JSON: {"issues": [...], "total": <int>}. "total" is the true
    Jira-side match count (use it for "how many" questions even if only a
    page of "issues" is returned).
    """
    settings = get_settings()
    project_key = settings.jira_project_key or "DEMO"
    scoped_jql = scope_and_validate_jql(jql, project_key)
    result = await JiraClient(settings).search(scoped_jql)
    return json.dumps(result.model_dump())


@tool
def calculate_sprint_metrics(issue_payload: str) -> str:
    """Compute blocker, bug-trend, velocity, and team-load metrics from Jira issues.

    issue_payload must be the JSON array found under the "issues" key of a
    prior jira_search result (pass it through verbatim). Use this whenever a
    question needs aggregation/analysis rather than a raw issue list —
    counts by assignee, story points completed per sprint, blocker lists,
    bug counts per sprint, etc.
    """
    from .domain import JiraIssue

    payload = json.loads(issue_payload)
    issues = [JiraIssue.model_validate(item) for item in payload]
    return json.dumps(
        {
            "blockers": blocker_analysis(issues),
            "bug_trend": bug_trend(issues),
            "velocity": sprint_velocity(issues),
            "team_load": team_load(issues),
        }
    )


@tool
async def current_sprint_name() -> str:
    """Return the name of the currently active sprint on the configured board, if known."""
    settings = get_settings()
    name = await JiraClient(settings).get_active_sprint()
    return name or "No active sprint is configured/known for this board."


@tool
def knowledge_search(query: str) -> str:
    """Search ingested RTB/Jira documentation (process docs, definitions, policies).

    Use this for conceptual or process questions ("what is spillover?", "what's
    our definition of done?") rather than for questions about specific issues,
    which should use jira_search instead.
    """
    service = RAGService()
    try:
        results = service.search(query, k=4)
    except Exception as exc:  # noqa: BLE001 - surface as a tool result, not a crash.
        return json.dumps({"results": [], "error": str(exc)})
    return json.dumps(
        {
            "results": [
                {"content": item["content"], "source": item.get("metadata", {}).get("source")}
                for item in results
            ]
        }
    )


AGENT_TOOLS = [jira_search, calculate_sprint_metrics, current_sprint_name, knowledge_search]
