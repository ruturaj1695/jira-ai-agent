# RTB Architecture

This implementation is derived from the RTB Cycle 16 PDF and follows its Jira Agent case study.

## Target flow

```text
User Query
   |
   v
FastAPI API
   |
   v
Guardrails
   |
   v
Router Agent (LangGraph)
   |
   v
Data Retrieval Agent
   |-------------> Jira API Tool
   |
   v
Analytics Agent
   |-------------> Python analytics/tool layer
   |
   v
Reporting Agent
   |
   v
Structured natural-language response
```

RAG is a separate knowledge path for Jira documentation, metadata, and other unstructured context:

```text
Documents -> chunking -> embeddings -> Chroma -> semantic retrieval -> agent context
```

## RTB milestone mapping

| RTB milestone | Repository implementation |
|---|---|
| 1. Foundations | `docs/`, prompt/agent design, provider configuration |
| 2. LLM building blocks | `rag.py`, embeddings/Chroma integration, analytics |
| 3. LangChain | `tools.py`, LangChain tools, model integration seam |
| 4. Agentic systems | `agents.py`, Router + Data + Analytics + Report graph |
| 5. Enterprise design | `guardrails.py`, config-driven secrets, deterministic analytics |
| 6. Productionization | FastAPI API, tests, Docker/CI planned |

## Agent responsibilities

- **Router Agent:** classify intent and select the worker path.
- **Data Agent:** retrieve Jira issues through the Jira adapter.
- **Analytics Agent:** calculate deterministic metrics rather than asking the LLM to perform arithmetic.
- **Reporting Agent:** turn validated analysis into a structured answer.

## Design principles

1. Keep Jira access behind an adapter so demo data and real Jira can share the same contract.
2. Keep analytics deterministic and testable.
3. Keep secrets in environment variables; never commit `.env`.
4. Use an LLM for language/reasoning, not as the source of truth for Jira metrics.
5. Preserve source metadata so answers can expose where data came from.
6. Add evaluation and observability before calling the system production-ready.
