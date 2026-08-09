from __future__ import annotations

from typing import Any

import httpx

from .config import Settings
from .domain import JiraIssue, JiraSearchResult


class JiraClient:
    """Small Jira adapter. Uses Jira Cloud REST when configured; demo data otherwise."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.jira_base_url
            and self.settings.jira_email
            and self.settings.jira_api_token
        )

    async def search(self, jql: str, max_results: int = 50) -> JiraSearchResult:
        if not self.configured:
            return self._demo_search(jql)

        url = f"{self.settings.jira_base_url.rstrip('/')}/rest/api/3/search"
        async with httpx.AsyncClient(timeout=20) as client:
            response = await client.get(
                url,
                params={"jql": jql, "maxResults": max_results},
                auth=(self.settings.jira_email, self.settings.jira_api_token),
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        issues = [self._map_issue(item) for item in payload.get("issues", [])]
        return JiraSearchResult(issues=issues, total=payload.get("total", len(issues)))

    def _map_issue(self, item: dict[str, Any]) -> JiraIssue:
        fields = item.get("fields", {})
        assignee = fields.get("assignee") or {}
        return JiraIssue(
            key=item["key"],
            summary=fields.get("summary", ""),
            status=(fields.get("status") or {}).get("name", "Unknown"),
            issue_type=(fields.get("issuetype") or {}).get("name", "Task"),
            priority=(fields.get("priority") or {}).get("name", "Medium"),
            assignee=assignee.get("displayName"),
            sprint=self._sprint_name(fields.get("sprint")),
            story_points=fields.get("customfield_10016") or 0,
            labels=fields.get("labels") or [],
        )

    @staticmethod
    def _sprint_name(sprint: Any) -> str | None:
        if isinstance(sprint, list) and sprint:
            sprint = sprint[-1]
        if isinstance(sprint, dict):
            return sprint.get("name")
        return None

    @staticmethod
    def _demo_search(jql: str) -> JiraSearchResult:
        data = [
            JiraIssue(key="DEMO-101", summary="Payment API timeout", status="Blocked", issue_type="Bug", priority="High", assignee="Asha", sprint="Sprint 24", story_points=5),
            JiraIssue(key="DEMO-102", summary="Checkout validation", status="Done", issue_type="Story", priority="Medium", assignee="Rahul", sprint="Sprint 24", story_points=8),
            JiraIssue(key="DEMO-103", summary="Mobile crash on login", status="In Progress", issue_type="Bug", priority="High", assignee="Neha", sprint="Sprint 24", story_points=3),
            JiraIssue(key="DEMO-104", summary="Invoice export", status="To Do", issue_type="Story", priority="Medium", assignee="Asha", sprint="Sprint 24", story_points=5),
            JiraIssue(key="DEMO-105", summary="Legacy tax defect", status="Done", issue_type="Bug", priority="Low", assignee="Rahul", sprint="Sprint 23", story_points=3),
            JiraIssue(key="DEMO-106", summary="Search indexing", status="Done", issue_type="Task", priority="Medium", assignee="Neha", sprint="Sprint 23", story_points=8),
        ]
        normalized = jql.lower()
        if "bug" in normalized:
            data = [item for item in data if item.issue_type.lower() == "bug"]
        if "blocked" in normalized:
            data = [item for item in data if item.status.lower() == "blocked"]
        return JiraSearchResult(issues=data, total=len(data))
