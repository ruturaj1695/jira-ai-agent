from rtb_jira_ai_agent.agents import classify_intent
from rtb_jira_ai_agent.analytics import blocker_analysis, sprint_velocity
from rtb_jira_ai_agent.domain import JiraIssue


def test_classify_blockers() -> None:
    assert classify_intent("What are the blockers in current sprint?") == "blockers"


def test_classify_velocity() -> None:
    assert classify_intent("Show sprint velocity") == "velocity"


def test_blocker_analysis() -> None:
    issues = [
        JiraIssue(key="A-1", summary="x", status="Blocked", priority="High"),
        JiraIssue(key="A-2", summary="y", status="Done", priority="Medium"),
    ]
    result = blocker_analysis(issues)
    assert result["count"] == 1
    assert result["high_priority"] == ["A-1"]


def test_velocity_only_counts_done_work() -> None:
    issues = [
        JiraIssue(key="A-1", summary="x", status="Done", sprint="Sprint 1", story_points=5),
        JiraIssue(key="A-2", summary="y", status="In Progress", sprint="Sprint 1", story_points=8),
    ]
    assert sprint_velocity(issues) == {"Sprint 1": 5}
