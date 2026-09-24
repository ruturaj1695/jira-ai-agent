# RTB Architecture

This implementation is derived from the RTB Cycle 16 PDF and follows its Intelligent Jira Agent case study. The PDF calls for query understanding, tool selection, Router + worker agents, Jira integration, optional vector search, Python analytics, structured reporting, security, observability, evaluation, and API deployment.

## Runtime flow

Two paths exist, selected at the graph's entry point based on whether an LLM
provider is configured (`LLMService.available()`).

**Primary path — tool-calling agent (LLM configured).** The model is not
restricted to a fixed set of intents. It is given a small toolbox and
decides at inference time which tool(s) to call, in what order, and how to
combine results — a standard ReAct-style agent loop
(`langgraph.prebuilt.create_react_agent`), not a rule-based router. This is
what lets the agent answer arbitrary phrasing rather than only the questions
a keyword list anticipated.

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
Tool-Calling Agent (Ollama/OpenAI + LangGraph ReAct loop)
   |
   +-- jira_search(jql)            -> Jira API Tool (project-scoped, read-only)
   +-- calculate_sprint_metrics()  -> Python analytics tools
   +-- current_sprint_name()       -> Jira Agile API
   +-- knowledge_search(query)     -> Ollama Embeddings -> Chroma
   |
   v
Final Answer (written by the model from tool results)
```

**Fallback path — deterministic pipeline (no LLM configured).** Used only
when no model is reachable (offline/demo mode). This is the original
fixed-intent graph: a keyword classifier buckets the query into one of a
small set of intents, each with its own hardcoded JQL template and answer
template. It can only answer the question shapes it was explicitly written
for.

```text
User Query
   |
   v
FastAPI API -> Guardrails -> Conversation Memory
   |
   v
Router Agent (deterministic keyword classifier)
   |
   +------------------------------+
   |                              |
   v                              v
Data Retrieval Agent          Knowledge Agent
   |                              |
Jira API Tool               Ollama Embeddings -> Chroma
   |                              |
   +---------------+--------------+
                   v
            Analytics Agent (Python analytics tools)
                   v
             Report Agent (template answers)
                   v
              Final Answer
```

If the tool-calling agent path throws (e.g. a transient model error), the
graph degrades to the deterministic pipeline for that request rather than
failing outright.

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
| 4. Agentic systems | `agents.py`/`tools.py`, LangGraph ReAct tool-calling agent (primary) + deterministic Router/worker fallback |
| 5. Enterprise design | guardrails, configuration-driven secrets, deterministic analytics |
| 6. Productionization | FastAPI, Docker, CI, tests, runtime status endpoint |

## Agent responsibilities

**Tool-calling agent (primary, LLM configured):**
- **jira_search:** the only way to read Jira issues; accepts a JQL *filter* from the model, but project scope and ordering are always applied by application code (`scope_and_validate_jql`), never by the model.
- **calculate_sprint_metrics:** deterministic Python aggregation (blockers, bug trend, velocity, team load) over a prior `jira_search` result — the LLM is never asked to do arithmetic itself.
- **current_sprint_name:** looks up the active sprint from the Jira Agile API.
- **knowledge_search:** semantic retrieval over ingested RTB/Jira documentation via Chroma.
- The model chains these as needed and writes the final natural-language answer from their outputs.

**Deterministic pipeline (fallback, no LLM configured):**
- **Router Agent:** classify intent by keyword and select the Jira or knowledge path.
- **Data Retrieval Agent:** retrieve authoritative Jira issues through the Jira adapter.
- **Knowledge Agent:** retrieve relevant unstructured project knowledge from Chroma.
- **Analytics Agent:** calculate deterministic metrics rather than asking the LLM to perform arithmetic.
- **Reporting Agent:** turn validated analysis/context into a concise, templated answer.

## Security boundaries

1. User input is validated before entering the graph.
2. Common prompt-injection attempts are rejected.
3. Jira access remains behind an application-owned adapter/tool in both paths.
4. JQL project scope and ordering are always applied by application code, in both paths — the model (deterministic or LLM-driven) only ever supplies a filter, and `scope_and_validate_jql` rejects any model-authored project clause, statement separators, or write-shaped input before it reaches Jira.
5. Secrets are environment variables only.
6. The tool-calling agent's system prompt requires every concrete fact in an answer to come from a tool result, not the model's own recollection; the deterministic path's report step is likewise instructed to use only validated analysis/context.

## Known limitations before final RTB submission

- Historical sprint commitment/completion data needs to be connected to the real Jira dataset for accurate spillover.
- RBAC enforcement needs to be wired to the organization's identity/access model.
- LangSmith/OpenTelemetry tracing and richer operational metrics need to be enabled.
- RAGAS-based evaluation needs to be added for retrieval and answer quality.
- Final failure-case evaluation, demo script, and evaluation report need to be completed.
