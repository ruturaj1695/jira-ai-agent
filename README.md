# RTB Jira AI Agent

Implementation of the **RTB Cycle 16 - Agentic AI: Building AI Agents (Basic)** Jira case study.

The architecture is based on the provided RTB PDF: natural-language Jira queries, query understanding, API/vector tool selection, Router + worker agents, reporting, RAG, security, evaluation, and production-oriented API design.

## Architecture

```text
User -> FastAPI -> Guardrails -> Router Agent
                                  |
                +-----------------+------------------+
                |                                    |
                v                                    v
        Data Retrieval Agent                   RAG / Knowledge Agent
                |                                    |
           Jira API Tool                       Chroma + Ollama
                |                                    |
                +-----------------+------------------+
                                  v
                           Analytics Agent
                                  |
                         Python analytics tools
                                  |
                                  v
                            Report Agent
                                  |
                             Ollama LLM
                                  |
                                  v
                              Answer
```

## Current implementation

- FastAPI `/health`
- FastAPI `/api/v1/status`
- FastAPI `/api/v1/query`
- Conversation memory using `conversation_id`
- LangGraph orchestration
- Ollama-backed Router/Report LLM (`llama3:8b` by default)
- Ollama-backed embeddings (`qwen3-embedding:latest` by default)
- Optional OpenAI fallback for local experimentation
- Router agent with deterministic fallback
- Data retrieval agent
- Conservative JQL generation
- Jira Cloud REST adapter
- Demo Jira dataset fallback for development
- LangChain Jira and analytics tools
- Chroma RAG service
- Document chunking and knowledge ingestion CLI
- RTB case-study knowledge source under `data/knowledge/`
- Prompt-injection guardrails
- Deterministic blocker, bug-trend, velocity, and team-load analytics
- Offline evaluation harness
- Pytest coverage
- Ruff CI
- Dockerfile
- Architecture documentation

## Company-provided Ollama environment

The RTB orientation communication provides dedicated Ollama servers and requires GlobalProtect VPN access. Do not commit the supplied credentials to this repository.

Configure the server URL locally in `.env`:

```env
OLLAMA_BASE_URL=<company-ollama-server-url>
LLM_PROVIDER=ollama
LLM_MODEL=llama3:8b
OLLAMA_EMBEDDING_MODEL=qwen3-embedding:latest
```

The repository intentionally does **not** contain the internal server credentials.

LangChain's current Ollama integration provides `ChatOllama` for chat models and `OllamaEmbeddings` for embeddings, which are the integrations used by this project. urlChatOllama documentationhttps://docs.langchain.com/oss/python/integrations/chat/ollama urlOllamaEmbeddings documentationhttps://docs.langchain.com/oss/python/integrations/embeddings/ollama

## Local setup

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Connect to the company VPN, set `OLLAMA_BASE_URL`, and start:

```bash
uvicorn rtb_jira_ai_agent.main:app --app-dir src --reload
```

Check runtime configuration:

```text
GET http://localhost:8000/api/v1/status
```

Run a Jira question:

```bash
curl -X POST http://localhost:8000/api/v1/query \\
  -H "Content-Type: application/json" \\
  -d '{"conversation_id":"demo","query":"What are blockers in current sprint?"}'
```

Without Jira credentials or an Ollama URL, the service still works in deterministic/demo mode. Configure Jira variables to use real Jira data and Ollama variables to enable the LLM layer.

## RAG knowledge ingestion

The included RTB knowledge source can be indexed after the Ollama embedding server is configured:

```bash
PYTHONPATH=src python scripts/ingest_knowledge.py data/knowledge/rtb_case_study.md
```

Then ask a knowledge question:

```bash
curl -X POST http://localhost:8000/api/v1/query \\
  -H "Content-Type: application/json" \\
  -d '{"conversation_id":"demo","query":"What is the role of the Router Agent?"}'
```

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

The baseline checks representative intent classification and response generation. The final RTB package still needs deeper evaluation of RAG retrieval, faithfulness, answer relevancy, tool selection, latency, failure cases, and improvements.
