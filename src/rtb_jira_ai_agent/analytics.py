from collections import Counter

from .domain import JiraIssue


def blocker_analysis(issues: list[JiraIssue]) -> dict:
    blockers = [i for i in issues if i.status.lower() in {"blocked", "impediment"}]
    return {
        "count": len(blockers),
        "issues": [i.key for i in blockers],
        "high_priority": [i.key for i in blockers if i.priority.lower() == "high"],
    }


def bug_trend(issues: list[JiraIssue]) -> dict[str, int]:
    counts = Counter(i.sprint or "Unknown" for i in issues if i.issue_type.lower() == "bug")
    return dict(counts)


def team_load(issues: list[JiraIssue]) -> dict[str, float]:
    result: Counter[str] = Counter()
    for issue in issues:
        if issue.assignee:
            result[issue.assignee] += issue.story_points
    return dict(result)


def sprint_velocity(issues: list[JiraIssue]) -> dict[str, float]:
    result: Counter[str] = Counter()
    for issue in issues:
        if issue.sprint and issue.status.lower() == "done":
            result[issue.sprint] += issue.story_points
    return dict(result)
