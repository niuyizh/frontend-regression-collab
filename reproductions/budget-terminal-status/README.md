# Structured workflow agent budget-stop status reproduction

This offline reproduction targets OpenCollab 0.9.6 at commit
`78ca8e374181f621e70e8d5436199182f8295cbf`. It uses no provider or API key.

Run it from the OpenCollab checkout so the reproduction imports that exact
source revision:

```bash
cd /path/to/OpenCollab
uv run python /path/to/frontend-regression-collab/reproductions/budget-terminal-status/reproduce.py
```

The scripted sessions stop with a budget terminal reason. A schema-bound
`ctx.agent(...)` performs its normal corrective retry, then returns `None`.
Both stopped sessions remain visible in `ctx.sessions`, while
`ctx.agent_failures` is empty:

```text
ctx.agent return: null
ctx.agent_failures: []
child_sessions[0].phase: stopped
child_sessions[1].phase: stopped
```

In the motivating live run, the authored workflow returned normally after this
condition. Consequently, its top-level `workflow.json` contained
`status: completed`, `reason: null`, and `failure_type: null`, even though both
child session terminal records contained the budget-stop reason. The live run
used DeepSeek's Responses-compatible endpoint, but this reproduction shows that
the status loss is provider-independent.

Expected improvement: expose a status-bearing result for schema-bound workflow
agents, analogous to `ctx.agent_run()`, or provide a public child-outcome list.
The outer workflow should remain free to recover a stopped child rather than
being forced to fail automatically.
