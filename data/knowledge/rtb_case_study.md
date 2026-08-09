# RTB Cycle 16 — Intelligent Jira Agent

This is a concise implementation-oriented knowledge source for the RTB case study. The original RTB PDF remains the authoritative source for evaluation requirements.

## Objective

Build an agentic Jira system that can answer natural-language questions, generate reports, and provide actionable insights from Jira project data.

## Expected Jira inputs

- Issues and their fields
- Sprints and historical sprint information
- Comments
- Assignees and team-related information
- Velocity metrics

## Example user questions

- What are the blockers in the current sprint?
- Which team has the highest spillover?
- Show the bug trend over the last three sprints.
- Show sprint risks.
- Generate a sprint summary.
- Provide team performance insights.

## Agent responsibilities

### Router Agent

Understand the user request and select the appropriate worker path.

### Data Retrieval Agent

Retrieve authoritative Jira information through the Jira API tool.

### Analytics Agent

Run deterministic calculations using Python-based tools for metrics such as blockers, bugs, velocity, and team load.

### Reporting Agent

Convert validated data and analysis into a concise natural-language response or structured report.

## Tool selection

The architecture can choose between Jira API retrieval and vector search. Jira is the source of truth for structured project metrics. Vector search is intended for unstructured project knowledge and documentation.

## RAG flow

Documents are chunked, embedded, stored in Chroma, retrieved using semantic similarity, and supplied as grounded context to the reporting layer.

## Production expectations

The RTB expects modular, production-oriented code with separation of concerns and configuration-driven design. The system should include logging, error handling, evaluation metrics, API/service deployment, security controls, prompt-injection safeguards, and appropriate observability.

## Evaluation

The final evaluation should report accuracy, representative failure cases, and improvements. For RAG, useful measurements include context precision, context recall, faithfulness, and answer relevancy.
