from fastapi import FastAPI

from . import __version__

app = FastAPI(
    title="RTB Jira AI Agent",
    version=__version__,
    description="Agentic AI service for Jira question answering and reporting.",
)


@app.get("/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok", "service": "rtb-jira-ai-agent"}
