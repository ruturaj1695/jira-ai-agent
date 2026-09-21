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
- Natural-language-to-JQL generation through the configured Ollama model
- Project-scoped, read-only JQL execution against live Jira
- Jira Cloud REST adapter using the current enhanced JQL search endpoint with legacy fallback
- Configurable Jira TLS verification / corporate CA bundle support
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

Connect to the company VPN, set `OLLAMA_BASE_URL` to the exact internal server endpoint supplied by the company, and start:

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
- optional `JIRA_BOARD_ID` for active-sprint lookups
- optional `JIRA_STORY_POINTS_FIELD` when the Jira installation uses a custom story-points field
- `JIRA_SSL_VERIFY=true` by default
- optional `JIRA_CA_BUNDLE` for the company-approved CA certificate

Never commit `.env` or API tokens.

### Live Jira behavior

When Jira credentials and a project key are configured, non-knowledge queries are executed against the configured Jira project. With Ollama available, the router asks the model to translate the natural-language request into read-only, project-scoped JQL; the resulting JQL is then sent to Jira and the response is analyzed by Python. The application does not use the demo issue dataset in live mode.

If Ollama is unavailable, the application falls back to deterministic JQL rules. Those fallback rules intentionally cover a smaller set of known intents; full natural-language Jira search requires the configured LLM.

The current Jira client uses `POST /rest/api/3/search/jql` first and falls back to the older `/rest/api/3/search` endpoint when necessary. The Jira Software sprint lookup uses `/rest/agile/1.0/board/{boardId}/sprint`.

## RTB milestone mapping

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the mapping from the six RTB milestones and mandatory deliverables to repository components.

## Evaluation

Run the baseline evaluation with:

```bash
PYTHONPATH=src python scripts/evaluate.py
```

The baseline checks representative intent classification and response generation. The final RTB package still needs deeper evaluation of RAG retrieval, faithfulness, answer relevancy, tool selection, latency, failure cases, and improvements.


## Corporate TLS troubleshooting

If live Jira calls fail with `SSL: CERTIFICATE_VERIFY_FAILED` and a self-signed certificate message:

1. Prefer the company-approved CA/root certificate and set `JIRA_CA_BUNDLE=<path-to-ca-bundle>`.
2. Keep `JIRA_SSL_VERIFY=true`.
3. For temporary local diagnosis only, `JIRA_SSL_VERIFY=false` disables certificate verification. Do not use this as the final enterprise configuration.

The RTB orientation screenshot provides three internal Ollama server addresses and lists the available models, but it does not show the HTTP protocol/port. Do not hard-code those internal addresses or credentials into the repository; use the exact endpoint provided by the company/GlobalProtect environment.
