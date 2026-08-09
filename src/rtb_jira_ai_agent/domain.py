from typing import Any, Literal

from pydantic import BaseModel, Field


class JiraIssue(BaseModel):
    key: str
    summary: str
    status: str
    issue_type: str = "Task"
    priority: str = "Medium"
    assignee: str | None = None
    sprint: str | None = None
    story_points: float = 0
    labels: list[str] = Field(default_factory=list)
    comments: list[str] = Field(default_factory=list)


class JiraSearchResult(BaseModel):
    issues: list[JiraIssue] = Field(default_factory=list)
    total: int = 0


class QueryRequest(BaseModel):
    query: str = Field(min_length=3)


class AgentResponse(BaseModel):
    answer: str
    intent: str
    sources: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


Intent = Literal["blockers", "bugs_trend", "spillover", "velocity", "search", "report", "unknown"]
