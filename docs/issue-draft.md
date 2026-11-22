# OpenCollab issue draft

Proposed title: `Schema-bound workflow agents do not expose budget-stop status`

Submitted: https://github.com/RISE-X-Lab/OpenCollab/issues/275

## What happened?

In an authored Workflow, `ctx.agent(..., schema=...)` can create child sessions
that stop because their token budget cannot reserve another model call. The call
returns `None`, but `ctx.agent_failures` remains empty because the stop is not an
exception. If the workflow function returns normally, the top-level workflow is
recorded as completed with no reason.

I expected a public, machine-readable way to distinguish a budget-stopped
schema-bound agent from a model that completed without satisfying the schema.
`ctx.agent_run()` already returns a status-bearing `WorkflowAgentResult`, but it
does not accept `schema=`.

This affects automated evaluations: a harness that checks only the workflow
status and `agent_failures` can accept an incomplete coding run as a successful
or valid run. It does not imply that every child stop should automatically fail
the parent workflow, because a workflow may intentionally recover from it.

## Steps to reproduce

No provider or API key is required.

```bash
git checkout 78ca8e374181f621e70e8d5436199182f8295cbf
uv sync --locked --extra dev
uv run python /path/to/reproduce.py
```

`reproduce.py` is included at
[`reproductions/budget-terminal-status/reproduce.py`](https://github.com/niuyizh/frontend-regression-collab/blob/main/reproductions/budget-terminal-status/reproduce.py)
in the accompanying project.
It creates two scripted sessions that stop with a budget terminal reason and
calls `ctx.agent(..., schema=...)`.

Observed output:

```json
{
  "ctx.agent return": null,
  "ctx.agent_failures": [],
  "child_sessions": [
    {"phase": "stopped", "terminal_reason": "budget exhausted before model call: ..."},
    {"phase": "stopped", "terminal_reason": "budget exhausted before model call: ..."}
  ]
}
```

The same condition occurred in a live DeepSeek Responses-compatible run. Its
saved top-level `workflow.json` had `status: completed`, `reason: null`, and
`failure_type: null`; both child `session_terminal` records contained the
budget-stop reason. Secrets and endpoint details are omitted.

## Orchestration mode

Workflow

## Interface

CLI (authored Python Workflow)

## Model & provider

Provider-independent offline reproduction. The motivating live run used
DeepSeek Flash through the official Responses-compatible API.

## OpenCollab version / commit

0.9.6 / `78ca8e374181f621e70e8d5436199182f8295cbf`

## Proposed improvement

Expose status-bearing structured calls, for example by allowing `schema=` on
`ctx.agent_run()` or adding a parallel result API whose output may be a validated
dictionary. The result should include `status`, `reason`, tokens, and the final
structured output. Existing `ctx.agent()` behavior can remain compatible.

An alternative is a public per-child outcome list on `WorkflowContext`.
Automatically failing the parent on any stopped child is not proposed because
it would prevent deliberate recovery workflows.

Expected benefit: evaluation harnesses and authored workflows can reject or
recover incomplete child work without reading private session state or parsing
JSONL traces. Cost: a wider public result API and compatibility tests for the
structured retry's multiple child sessions.

## Existing issue search

On 2026-11-22, all three pages of the repository's GitHub Issues API were
checked (`state=all`, 274 returned items). Every returned item was a pull
request; there were no standalone issues and therefore no same-topic issue to
extend.
