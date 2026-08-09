from langchain_core.messages import HumanMessage, SystemMessage

from .config import Settings


class LLMService:
    """Optional LLM facade. The core analytics path remains deterministic without a key."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def available(self) -> bool:
        return bool(self.settings.openai_api_key)

    async def format_report(self, query: str, analysis: dict) -> str:
        if not self.available():
            return ""
        from langchain_openai import ChatOpenAI

        model = ChatOpenAI(
            model=self.settings.llm_model,
            api_key=self.settings.openai_api_key,
            temperature=0,
        )
        messages = [
            SystemMessage(
                content=(
                    "You are an enterprise Jira reporting assistant. "
                    "Use only the supplied analysis. Do not invent Jira facts. "
                    "Return a concise, structured answer with risks and next actions when supported."
                )
            ),
            HumanMessage(content=f"Query: {query}\nValidated analysis: {analysis}"),
        ]
        response = await model.ainvoke(messages)
        return str(response.content)
