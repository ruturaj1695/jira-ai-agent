from __future__ import annotations

from typing import Any

import httpx

from .config import Settings
from .domain import JiraIssue, JiraSearchResult


class JiraClient:
    """Jira REST adapter with a safe demo fallback for local development."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def configured(self) -> bool:
        return bool(
            self.settings.jira_base_url
            and self.settings.jira_email
            and self.settings.jira_api_token
        )

    @property
    def live_scope_configured(self) -> bool:
        """Real Jira search requires a project scope to avoid cross-project queries."""
        return self.configured and bool(self.settings.jira_project_key)

    def _verify_ssl(self) -> bool | str:
        """Return True/False or a CA bundle path for Jira TLS verification."""
        if self.settings.jira_ca_bundle:
            return self.settings.jira_ca_bundle
        return self.settings.jira_ssl_verify

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            timeout=20,
            verify=self._verify_ssl(),
            follow_redirects=True,
        )

    def _auth(self) -> tuple[str, str]:
        if not self.configured:
            raise RuntimeError("Jira credentials are not configured")
        return (
            self.settings.jira_email or "",
            self.settings.jira_api_token or "",
        )

    async def get_active_sprint(self) -> str | None:
        """
        Fetch the currently active sprint from the configured Jira Software board.
        Uses the Jira Software Agile REST API.
        """
        if not self.configured or not self.settings.jira_board_id:
            return None

        url = (
            f"{self.settings.jira_base_url.rstrip('/')}"
            f"/rest/agile/1.0/board/{self.settings.jira_board_id}/sprint"
        )
        async with self._client() as client:
            response = await client.get(
                url,
                params={"state": "active", "maxResults": 1},
                auth=self._auth(),
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            payload: dict[str, Any] = response.json()
        sprints = payload.get("values", [])
        if not sprints:
            return None
        return sprints[0].get("name")

    async def search(self, jql: str, max_results: int | None = None) -> JiraSearchResult:
        """
        Execute JQL against live Jira when configured.

        The current Jira Cloud enhanced search endpoint is used first. A legacy
        /rest/api/3/search fallback is retained for installations that still expose it.
        """
        if not self.configured:
            return self._demo_search(jql)

        if not self.live_scope_configured:
            raise RuntimeError(
                "JIRA_PROJECT_KEY is required for live Jira search so the agent "
                "cannot accidentally query across projects."
            )

        limit = max_results or self.settings.jira_max_results
        base_url = self.settings.jira_base_url.rstrip("/")
        headers = {"Accept": "application/json"}

        fields = [
            "summary",
            "status",
            "issuetype",
            "priority",
            "assignee",
            "labels",
            "sprint",
        ]
        if self.settings.jira_story_points_field:
            fields.append(self.settings.jira_story_points_field)

        async with self._client() as client:
            response = await client.post(
                f"{base_url}/rest/api/3/search/jql",
                json={
                    "jql": jql,
                    "maxResults": limit,
                    "fields": fields,
                },
                auth=self._auth(),
                headers={**headers, "Content-Type": "application/json"},
            )

            if response.status_code in {404, 405}:
                # Compatibility fallback for older Jira Cloud/server configurations.
                response = await client.get(
                    f"{base_url}/rest/api/3/search",
                    params={
                        "jql": jql,
                        "maxResults": limit,
                        "fields": ",".join(fields),
                    },
                    auth=self._auth(),
                    headers=headers,
                )

            response.raise_for_status()
            payload: dict[str, Any] = response.json()

        issues = [self._map_issue(item) for item in payload.get("issues", [])]
        return JiraSearchResult(issues=issues, total=payload.get("total", len(issues)))

    def _map_issue(self, item: dict[str, Any]) -> JiraIssue:
        fields = item.get("fields", {})
        assignee = fields.get("assignee") or {}

        story_points = 0
        if self.settings.jira_story_points_field:
            story_points = fields.get(self.settings.jira_story_points_field) or 0
        if not story_points:
            # Keep the mapper safe when the installation uses a different custom field.
            story_points = fields.get("storyPoints") or 0

        return JiraIssue(
            key=item["key"],
            summary=fields.get("summary", ""),
            status=(fields.get("status") or {}).get("name", "Unknown"),
            issue_type=(fields.get("issuetype") or {}).get("name", "Task"),
            priority=(fields.get("priority") or {}).get("name", "Medium"),
            assignee=assignee.get("displayName"),
            sprint=self._sprint_name(fields.get("sprint")),
            story_points=story_points,
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
            JiraIssue(
                key="DEMO-101",
                summary="Payment API timeout",
                status="Blocked",
                issue_type="Bug",
                priority="High",
                assignee="Asha",
                sprint="Sprint 24",
                story_points=5,
            ),
            JiraIssue(
                key="DEMO-102",
                summary="Checkout validation",
                status="Done",
                issue_type="Story",
                priority="Medium",
                assignee="Rahul",
                sprint="Sprint 24",
                story_points=8,
            ),
            JiraIssue(
                key="DEMO-103",
                summary="Mobile crash on login",
                status="In Progress",
                issue_type="Bug",
                priority="High",
                assignee="Neha",
                sprint="Sprint 24",
                story_points=3,
            ),
            JiraIssue(
                key="DEMO-104",
                summary="Invoice export",
                status="To Do",
                issue_type="Story",
                priority="Medium",
                assignee="Asha",
                sprint="Sprint 24",
                story_points=5,
            ),
            JiraIssue(
                key="DEMO-105",
                summary="Legacy tax defect",
                status="Done",
                issue_type="Bug",
                priority="Low",
                assignee="Rahul",
                sprint="Sprint 23",
                story_points=3,
            ),
            JiraIssue(
                key="DEMO-106",
                summary="Search indexing",
                status="Done",
                issue_type="Task",
                priority="Medium",
                assignee="Neha",
                sprint="Sprint 23",
                story_points=8,
            ),
        ]
        normalized = jql.lower()
        if "bug" in normalized:
            data = [item for item in data if item.issue_type.lower() == "bug"]
        if "blocked" in normalized:
            data = [item for item in data if item.status.lower() == "blocked"]
        if "sprint" in normalized:
            for sprint_name in ["Sprint 24", "Sprint 23"]:
                if f'"{sprint_name.lower()}"' in normalized or f"'{sprint_name.lower()}'" in normalized:
                    data = [item for item in data if item.sprint == sprint_name]
                    break
        return JiraSearchResult(issues=data, total=len(data))
