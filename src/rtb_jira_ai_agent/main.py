import logging

from fastapi import FastAPI, HTTPException

from . import __version__
from .agents import agent_graph
from .config import get_settings
from .domain import AgentResponse, QueryRequest
from .guardrails import validate_user_query
from .jira_client import JiraClient
from .llm import LLMService
from .memory import conversation_memory
from .observability import request_logging_middleware
from .rag import RAGService

settings = get_settings()
logging.basicConfig(level=getattr(logging, settings.log_level.upper(), logging.INFO))

app = FastAPI(
    title="RTB Jira AI Agent",
    version=__version__,
    description="Agentic AI service for Jira question answering and reporting.",
)
app.middleware("http")(request_logging_middleware)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "rtb-jira-ai-agent"}


@app.get("/api/v1/status", tags=["system"])
def runtime_status() -> dict[str, object]:
    return {
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "llm_configured": LLMService(settings).available(),
        "jira_configured": JiraClient(settings).configured,
        "rag_configured": RAGService().available(),
        "chroma_persist_directory": settings.chroma_persist_directory,
    }


@app.post("/api/v1/query", response_model=AgentResponse, tags=["agent"])
async def query_agent(request: QueryRequest) -> AgentResponse:
    try:
        validate_user_query(request.query)
        history = conversation_memory.history(request.conversation_id)
        result = await agent_graph.ainvoke(
            {"query": request.query, "history": history}
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Agent execution failed") from exc

    answer = result.get("answer", "No answer generated.")
    conversation_memory.append(request.conversation_id, "user", request.query)
    conversation_memory.append(request.conversation_id, "assistant", answer)

    return AgentResponse(
        answer=answer,
        intent=result.get("intent", "unknown"),
        sources=result.get("sources", []),
        metadata={
            "conversation_id": request.conversation_id,
            "issue_count": result.get("jira_total", len(result.get("issues", []))),
            "returned_issue_count": len(result.get("issues", [])),
            "analysis": result.get("analysis", {}),
        },
    )
