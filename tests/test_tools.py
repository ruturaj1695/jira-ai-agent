import pytest

from rtb_jira_ai_agent.tools import scope_and_validate_jql


def test_scope_and_validate_jql_adds_project_and_order() -> None:
    jql = scope_and_validate_jql('issuetype = "Bug" AND assignee = currentUser()', "EDTGD")
    assert jql == (
        'project = "EDTGD" AND (issuetype = "Bug" AND assignee = currentUser()) '
        "ORDER BY updated DESC"
    )


def test_scope_and_validate_jql_handles_empty_filter() -> None:
    assert scope_and_validate_jql("", "EDTGD") == 'project = "EDTGD" ORDER BY updated DESC'


def test_scope_and_validate_jql_rejects_model_supplied_project_clause() -> None:
    with pytest.raises(ValueError, match="project clause"):
        scope_and_validate_jql('project = "OTHER"', "EDTGD")


def test_scope_and_validate_jql_rejects_statement_separators() -> None:
    with pytest.raises(ValueError, match="statement separators"):
        scope_and_validate_jql('issuetype = "Bug"; DROP', "EDTGD")


def test_scope_and_validate_jql_strips_model_supplied_order_by() -> None:
    jql = scope_and_validate_jql("ORDER BY created DESC", "EDTGD")
    assert jql == 'project = "EDTGD" ORDER BY updated DESC'
