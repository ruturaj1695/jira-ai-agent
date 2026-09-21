from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage

from .config import Settings
from .domain import Intent


class LLMService:
    """Provider-agnostic LLM facade with Ollama as the RTB default."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def available(self) -> bool:
        if self.settings.llm_provider.lower() == "ollama":
            return bool(self.settings.ollama_base_url)
        return bool(self.settings.openai_api_key)

    def _model(self):
        provider = self.settings.llm_provider.lower()
        if provider == "ollama":
            from langchain_ollama import ChatOllama

            return ChatOllama(
                model=self.settings.llm_model,
                base_url=self.settings.ollama_base_url,
                temperature=0,
            )
        if provider == "openai":
            from langchain_openai import ChatOpenAI

            return ChatOpenAI(
                model=self.settings.llm_model,
                api_key=self.settings.openai_api_key,
                temperature=0,
            )
        raise ValueError(f"Unsupported LLM provider: {self.settings.llm_provider}")

    async def format_report(
        self,
        query: str,
        analysis: dict[str, Any],
        history: list[dict[str, str]] | None = None,
    ) -> str:
        if not self.available():
            return ""
        try:
            model = self._model()
            history_text = json.dumps(history or [], default=str)
            messages = [
                SystemMessage(
                    content=(
                        "You are an enterprise Jira reporting assistant. "
                        "Use only the supplied validated analysis. Never invent Jira facts. "
                        "Use conversation history only to resolve references such as 'that sprint'. "
                        "Return a concise structured answer with findings, risks, and next actions "
                        "only when supported by the data."
                    )
                ),
                HumanMessage(
                    content=(
                        f"Conversation history: {history_text}\n"
                        f"Current query: {query}\n"
                        f"Validated analysis: {json.dumps(analysis, default=str)}"
                    )
                ),
            ]
            response = await model.ainvoke(messages)
            return str(response.content).strip()
        except Exception:  # noqa: BLE001 - LLM failures intentionally use the deterministic fallback.
            return ""


    async def generate_jql(
        self,
        query: str,
        project_key: str | None,
        history: list[dict[str, str]] | None = None,
    ) -> str | None:
        """Translate natural language into read-only, project-scoped JQL."""
        if not self.available() or not project_key:
            return None

        prompt = (
            "Translate the Jira user request into ONE valid Jira Cloud JQL expression. "
            "Return JSON only: {" + '"jql"' + ": " + '"..."' + "}. "
            "The application will add the project scope and ORDER BY clause, so do not include "
            "a project clause or ORDER BY. Never generate mutation/write operations. "
            "Prefer read-only Jira fields and functions such as summary, description, status, "
            "issuetype, priority, assignee, reporter, labels, sprint, created, updated, "
            "statusCategory, and openSprints(). "
            "For broad searches, use a sensible filter such as updated IS NOT EMPTY. "
            "For current-sprint questions, use sprint in openSprints() where appropriate. "
            f"Project scope is fixed by the application to {project_key}.\n"
            f"Conversation history: {json.dumps(history or [], default=str)}\n"
            f"User request: {query}"
        )
        try:
            response = await self._model().ainvoke([HumanMessage(content=prompt)])
            payload = json.loads(str(response.content))
            jql = payload.get("jql")
            if not isinstance(jql, str):
                return None

            normalized = jql.strip()
            lowered = normalized.lower()
            if not normalized or "project" in lowered or ";" in normalized:
                return None
            if lowered.startswith("order by"):
                return None

            return f'project = "{project_key}" AND ({normalized}) ORDER BY updated DESC'
        except Exception:  # noqa: BLE001 - invalid LLM output falls back to deterministic JQL.
            return None

    async def classify_intent(self, query: str) -> Intent | None:
        """Ask the configured LLM for intent classification; return None on any failure."""
        if not self.available():
            return None
        prompt = (
            "Classify the Jira user request into exactly one label: blockers, bugs_trend, "
            "spillover, velocity, search, report, knowledge, unknown. "
            "Return JSON only: {\"intent\": \"label\"}.\n\n"
            f"User request: {query}"
        )
        try:
            response = await self._model().ainvoke([HumanMessage(content=prompt)])
            payload = json.loads(str(response.content))
            intent = payload.get("intent")
            allowed = {
                "blockers",
                "bugs_trend",
                "spillover",
                "velocity",
                "search",
                "report",
                "knowledge",
                "unknown",
            }
            return intent if intent in allowed else None
        except Exception:  # noqa: BLE001 - classification failures fall back to deterministic routing.
            return None
