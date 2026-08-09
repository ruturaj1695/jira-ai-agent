import json

from langchain_core.tools import tool

from .analytics import blocker_analysis, bug_trend, sprint_velocity, team_load
from .config import get_settings
from .jira_client import JiraClient


@tool
async def jira_search(jql: str) -> str:
    """Search Jira using JQL. Returns a compact JSON representation of issues."""
    result = await JiraClient(get_settings()).search(jql)
    return json.dumps(result.model_dump())


@tool
def calculate_sprint_metrics(issue_payload: str) -> str:
    """Calculate blocker, bug, velocity, and team-load metrics from issue JSON."""
    from .domain import JiraIssue

    payload = json.loads(issue_payload)
    issues = [JiraIssue.model_validate(item) for item in payload]
    return json.dumps({
        "blockers": blocker_analysis(issues),
        "bug_trend": bug_trend(issues),
        "velocity": sprint_velocity(issues),
        "team_load": team_load(issues),
    })
