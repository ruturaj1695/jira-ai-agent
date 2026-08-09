# RTB Jira AI Agent

Implementation of the **RTB Cycle 16 - Agentic AI: Building AI Agents (Basic)** Jira case study.

The project follows the PDF requirements: natural-language Jira queries, intelligent routing, data retrieval, analytics, reporting, RAG, tools, guardrails, evaluation, and production-oriented API design.

## Architecture

```text
User -> FastAPI -> Guardrails -> Router Agent
                                  |
                                  v
                           Data Retrieval Agent
                                  |
                         Jira API / demo data
                                  |
                                  v
                            Analytics Agent
                                  |
                           Python analytics
                                  |
                                  v
                            Report Agent
                                  |
                                  v
                             Answer

Knowledge path: documents -> chunks -> embeddings -> Chroma -> semantic search
```

## Implemented now

- FastAPI `/health`
- FastAPI `/api/v1/query`
- LangGraph orchestration
- Router agent
- Data retrieval agent
- Analytics agent
- Reporting agent
- Jira Cloud REST adapter
- Demo Jira dataset fallback for local development
- LangChain tools
- Chroma RAG service
- Document chunking/ingestion
- Optional OpenAI report generation
- Prompt-injection guardrails
- Deterministic analytics for blockers, bugs, velocity, and team load
- Offline evaluation harness
- Pytest coverage
- Ruff CI
- Dockerfile
- Architecture documentation

## Local setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
uvicorn rtb_jira_ai_agent.main:app --app-dir src --reload
```

Then call:

```bash
curl -X POST http://localhost:8000/api/v1/query \\
  -H "Content-Type: application/json" \\
  -d '{"query":"What are blockers in current sprint?"}'
```

Without Jira credentials, the service uses a small demo dataset so the agent can be demonstrated immediately. Configure Jira variables in `.env` to use real Jira data.

## Jira configuration

Set:

- `JIRA_BASE_URL`
- `JIRA_EMAIL`
- `JIRA_API_TOKEN`
- `JIRA_PROJECT_KEY`

Never commit `.env` or API tokens.

## RTB milestone mapping

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the mapping from the six RTB milestones and mandatory deliverables to repository components.

## Evaluation

Run the baseline evaluation with:

```bash
PYTHONPATH=src python scripts/evaluate.py
```

The evaluation currently checks intent classification and non-empty answers for representative RTB queries. More rigorous faithfulness, grounding, hallucination, latency, and cost evaluation will be added before final submission.
