# Improvement validation: status-aware structured agents

## Scope

The project-side extension in `workflows/status_aware_agent.py` snapshots the
workflow's public session list before a schema-bound agent call. If the call
returns no validated dictionary, it promotes the newly created child session's
`stopped` or `error` phase and terminal reason into a `StructuredAgentOutcome`.
It does not automatically fail a parent workflow and does not alter OpenCollab.

## Before

The first live 16k calibration produced two stopped child sessions, a `None`
developer report, and an empty `agent_failures` list. The original project
workflow then returned `status: ok`. The external evaluator could therefore
score unchanged code without recognizing that the coding agent run was invalid.

## After

The workflow returns `status: incomplete` and records an outcome shaped as:

```json
{
  "output": null,
  "status": "stopped",
  "reason": "budget exhausted before model call",
  "sessions_started": 1
}
```

`scripts/evaluate_run.py` requires a valid workflow result before
`task_complete` can be true, and `scripts/run_experiment.py` labels this case
`invalid-agent-run`.

## Verification

The regression test
`test_status_aware_extension_preserves_structured_budget_stop_reason` injects the same
terminal condition without an API call. It verifies the exact status and reason
propagation. A second test checks the native status-bearing Developer path. The
complete project harness currently passes 11 tests, and Ruff passes.

## Trade-offs and applicability

This extension reads child session state because the current public structured
agent return value does not carry status. It is appropriate as a bounded project
workaround, but a framework result API would be more stable. A schema miss after
normally completed sessions is classified as `incomplete`, distinct from a
budget stop. A valid retry output is classified as completed even when an
earlier attempt stopped, because the requested structured result was recovered.
