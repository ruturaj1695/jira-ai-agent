# Prompt Engineering Lab

This document maps the RTB prompt-engineering hands-on requirement to reusable prompts in the Jira agent.

## Summarization

**Goal:** summarize only validated Jira analysis.

```text
You are an enterprise Jira reporting assistant.
Summarize only the validated analysis below.
Do not invent Jira facts.
Return: Summary, Key Risks, Recommended Actions.
```

## Q&A

**Goal:** answer from retrieved knowledge.

```text
Answer the question using only the supplied context.
If the context does not contain the answer, say that the knowledge base does not provide enough information.
Cite the supplied source names when available.
```

## Classification

**Goal:** route a Jira request.

```text
Classify the request into exactly one of:
blockers, bugs_trend, spillover, velocity, search, report, knowledge, unknown.
Return JSON only: {"intent":"<label>"}.
```

## Few-shot extension

For higher routing accuracy, add representative examples to the classification prompt and measure the change against the evaluation set. Do not add examples that leak real Jira credentials or confidential project data.

## ReAct / tool-use principle

The final agent should reason about which tool is needed, but the application must enforce tool permissions and validate tool arguments before execution. The LLM must never receive unrestricted access to Jira or arbitrary code execution.
