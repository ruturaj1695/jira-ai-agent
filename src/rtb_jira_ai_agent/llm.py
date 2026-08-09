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

    async def format_report(self, query: str, analysis: dict[str, Any]) -> str:
        if not self.available():
            return ""
        model = self._model()
        messages = [
            SystemMessage(
                content=(
                    "You are an enterprise Jira reporting assistant. "
                    "Use only the supplied validated analysis. Never invent Jira facts. "
                    "Return a concise structured answer with findings, risks, and next actions "
                    "only when supported by the data."
                )
            ),
            HumanMessage(content=f"Query: {query}\nValidated analysis: {json.dumps(analysis, default=str)}"),
        ]
        response = await model.ainvoke(messages)
        return str(response.content).strip()

    async def classify_intent(self, query: str) -> Intent | None:
        """Ask the configured LLM for intent classification; return None on any failure."""
        if not self.available():
            return None
        model = self._model()
        prompt = (
            "Classify the Jira user request into exactly one label: blockers, bugs_trend, "
            "spillover, velocity, search, report, knowledge, unknown. "
            "Return JSON only: {\"intent\": \"label\"}.\n\n"
            f"User request: {query}"
        )
        try:
            response = await model.ainvoke([HumanMessage(content=prompt)])
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
        except (ValueError, TypeError, json.JSONDecodeError):
            return None
