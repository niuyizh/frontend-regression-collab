# Artifact-first resilient handoff experiment

## Motivation

The frozen Single versus strict Dev-QA matrix produced multiple runs in which
the Developer had already changed the correct files, and often passed all
external tests, but its `agent_run()` stopped before a final narrative response.
The strict workflow rejected the run and never started QA. This is a workflow
handoff failure, distinct from a frontend implementation failure.

## Improvement

`frontend-dev-qa-resilient` keeps the same Developer, QA, and Repair prompts,
tools, role caps (30k/6k/18k), global 48k cap, model, tasks, and external
evaluator. It changes only the handoff rule:

1. A normally completed coding role hands off as before.
2. A `stopped` Developer may hand off only when cleanup and workspace state are
   valid and the Git diff is non-empty. Its stopped outcome and reason remain
   explicit; the diff, not partial prose, is authoritative.
3. A stopped Developer with no diff remains incomplete and QA is not started.
4. After a QA FAIL, a stopped Repair may hand off only if the post-repair diff
   is non-empty and differs from the pre-repair diff.
5. Recovery never determines task success. Build, all six public tests, both
   hidden tests, tamper checks, and a parseable QA verdict remain mandatory.

This is an orchestration-strategy improvement, not a framework patch. It uses
the status-bearing `agent_run()` API introduced into the project after the
schema-bound status-loss issue was found.

## Frozen comparison

The improvement runs once on all five tasks. T03 and T04 run three times because
they support the failure-recovery and responsive-boundary conclusions and showed
run-to-run variability. This yields nine resilient runs:

```text
5 tasks x 1 run + 2 key tasks x 2 additional runs = 9
```

The existing nine Single runs are the primary baseline. The existing nine
strict Dev-QA runs are the handoff-policy ablation. No Single or strict Dev-QA
result is rerun or selected post hoc. Resilient execution order is shuffled by
the fixed seed `20261122`.

## Metrics and interpretation

- task completion and agent-run validity;
- build, public regression, and hidden-test results;
- tokens and Agent wall time;
- Developer/Repair recovery counts;
- QA PASS/FAIL and whether a repair changed the final score;
- per-run results for T03 and T04.

An improvement is useful if it recovers valid externally passing work without
accepting empty or failing artifacts. Higher completion with higher token/time
cost is reported as a trade-off. Nine runs support this bounded project result,
not a universal frontend-agent claim.
