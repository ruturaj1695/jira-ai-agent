# RTB Architecture

This implementation is derived from the RTB Cycle 16 PDF and follows its Intelligent Jira Agent case study. The PDF calls for query understanding, tool selection, Router + worker agents, Jira integration, optional vector search, Python analytics, structured reporting, security, observability, evaluation, and API deployment.

## Runtime flow

```text
User Query
   |
   v
FastAPI API
   |
   v
Prompt-Injection Guardrails
   |
   v
Conversation Memory
   |
   v
Router Agent (Ollama / LangGraph)
   |
   +------------------------------+
   |                              |
   v                              v
Data Retrieval Agent          Knowledge Agent
   |                              |
Jira API Tool               Ollama Embeddings
   |                              |
   |                           Chroma
   |                              |
   +---------------+--------------+
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
              Final Answer
```

## Provider strategy

The company-provided Ollama environment is the default RTB runtime. The LLM provider and embedding model are configuration-driven so the implementation can be tested without external credentials and can optionally use a cloud provider for local experimentation.

Default models in `.env.example`:

- Chat: `llama3:8b`
- Embeddings: `qwen3-embedding:latest`

Internal server addresses and credentials are intentionally not committed.

## RAG flow

```text
Markdown/Text documents
        |
        v
Recursive chunking
        |
        v
Ollama embeddings
        |
        v
Chroma
        |
        v
Semantic retrieval
        |
        v
Knowledge Agent
        |
        v
Report Agent
```

The RTB PDF specifies document ingestion, chunking/embedding, Chroma storage, and semantic search + QA for the RAG hands-on. 

## RTB milestone mapping

| RTB milestone | Current repository coverage |
|---|---|
| 1. Foundations | `docs/PROMPT_ENGINEERING.md`, model/provider configuration |
| 2. LLM building blocks | Ollama chat, Ollama embeddings, Chroma, deterministic analytics |
| 3. LangChain | `tools.py`, LangChain tools, model integrations, conversation memory |
| 4. Agentic systems | `agents.py`, LangGraph Router + worker paths |
| 5. Enterprise design | guardrails, configuration-driven secrets, deterministic analytics |
| 6. Productionization | FastAPI, Docker, CI, tests, runtime status endpoint |

## Agent responsibilities

- **Router Agent:** classify intent and select the Jira or knowledge path.
- **Data Retrieval Agent:** retrieve authoritative Jira issues through the Jira adapter.
- **Knowledge Agent:** retrieve relevant unstructured project knowledge from Chroma.
- **Analytics Agent:** calculate deterministic metrics rather than asking the LLM to perform arithmetic.
- **Reporting Agent:** turn validated analysis/context into a concise structured answer.

## Security boundaries

1. User input is validated before entering the graph.
2. Common prompt-injection attempts are rejected.
3. Jira access remains behind an application-owned adapter/tool.
4. JQL is generated conservatively by application code; the LLM is not granted unrestricted Jira execution.
5. Secrets are environment variables only.
6. The LLM is instructed to use validated analysis/context and not invent Jira facts.

## Known limitations before final RTB submission

- Historical sprint commitment/completion data needs to be connected to the real Jira dataset for accurate spillover.
- RBAC enforcement needs to be wired to the organization's identity/access model.
- LangSmith/OpenTelemetry tracing and richer operational metrics need to be enabled.
- RAGAS-based evaluation needs to be added for retrieval and answer quality.
- Final failure-case evaluation, demo script, and evaluation report need to be completed.
