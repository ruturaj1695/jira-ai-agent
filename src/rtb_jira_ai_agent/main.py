from fastapi import FastAPI, HTTPException

from . import __version__
from .agents import agent_graph
from .domain import AgentResponse, QueryRequest
from .guardrails import validate_user_query

app = FastAPI(
    title="RTB Jira AI Agent",
    version=__version__,
    description="Agentic AI service for Jira question answering and reporting.",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "rtb-jira-ai-agent"}


@app.post("/api/v1/query", response_model=AgentResponse, tags=["agent"])
async def query_agent(request: QueryRequest) -> AgentResponse:
    try:
        validate_user_query(request.query)
        result = await agent_graph.ainvoke({"query": request.query})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=502, detail="Agent execution failed") from exc

    return AgentResponse(
        answer=result.get("answer", "No answer generated."),
        intent=result.get("intent", "unknown"),
        sources=result.get("sources", []),
        metadata={
            "issue_count": len(result.get("issues", [])),
            "analysis": result.get("analysis", {}),
        },
    )
