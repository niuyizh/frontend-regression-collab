# DesignBench adapter validation

## Scope decision

The selected DeepSeek endpoint exposed only `deepseek-flash` and
`deepseek-v4-pro` through `/models` on 2026-11-22; neither identifier indicates
vision support. OpenCollab's workflow API also cannot currently pass structured
image content to `agent_run()`. The external subset therefore uses
DesignBench's text-and-code (`code`) mode: four React Edit tasks and one Compile
task. The screenshot-dependent Repair task was removed.

## Frozen tasks

| Task | Scenario | Primary external signal |
|---|---|---|
| `db-e01` | Split a profile name field | DOM structure + visual progress |
| `db-e11` | Add delivery schedule controls | DOM structure + visual progress |
| `db-e27` | Reorganize an email toolbar | DOM/layout structure + visual progress |
| `db-e30` | Compact a toolbar while preserving content | DOM/layout structure + visual progress |
| `db-c06` | Repair a Client Component boundary | successful render |

Repository revision:
`a1e58d66ecbf1f77848bc5529ee7bbbe33bc25ba`.
Dataset revision: `a04022a331a8ad385dbbf26a1da9ca4a26a2628d`.

## Scoring protocol

Playwright Chromium renders at 1792×925 CSS pixels with device scale factor 2,
producing the benchmark's 3584×1850 PNG dimensions. The evaluator remains
outside the agent workspace and records:

- hidden task-specific DOM and computed-style checks;
- pixelmatch similarity;
- normalized RGB MAE similarity;
- relative MAE progress from the frozen initial page to the frozen gold page.

An Edit task passes when it renders, all structural checks pass, and relative
MAE progress is at least 0.5. Compile passes when the repaired page renders.
The threshold and calibration measurements are versioned in
`benchmark/designbench/scoring.json`.

All four Edit initial pages fail structural checks and all four gold pages pass.
The Compile initial page returns HTTP 500 with the missing Client Component
boundary error; its gold page returns HTTP 200.

The first paid `db-e30` calibration exposed two harness issues and is retained
as a failed pilot rather than treated as comparative evidence. First, the
structural check required the four leading buttons to be direct DOM children;
this rejected visually valid wrapper structures. The revised check uses button
geometry (four contiguous leading buttons independent of their wrappers).
Second, both agents read all 300 lines of `app/page.tsx`, including
irrelevant SVG definitions. The Dev-QA developer then exhausted its 30k role
budget after editing and public verification but before its final handoff, so
QA never ran. The task now supplies the already-known 63-90 source window and
requires a ranged read; no role or global budget was increased. Original pilot
artifacts remain under `results/designbench/raw/*__r1`.

## Paid calibration result

The post-pilot r2 pair used the same `deepseek-flash` endpoint, task prompt,
48k global cap, initial workspace, and scorer. Time below is OpenCollab agent
wall time and excludes the external evaluator.

| Condition | Valid | Task pass | Tokens | Time (s) | Visual progress |
|---|---:|---:|---:|---:|---:|
| Single r2 | yes | no | 14,333 | 25.962 | 0.103 |
| Dev-QA r2 | yes | yes | 24,532 | 50.830 | 0.798 |

Single preserved the outer `p-4`, but added unrequested blur, transparency,
`z-10`, and fixed button sizing. Its structural checks passed, while its visual
progress remained below the frozen 0.5 threshold. In Dev-QA, the first
Developer instead changed outer toolbar padding from `p-4` to `p-2`; the public
render smoke still passed. Regression QA cited that exact diff as a violation
of “Nothing else should change,” and the repair restored `p-4`. The final page
passed all structural checks and reached 0.798 visual progress.

This pair demonstrates the intended mechanism: an independent diff-only role
caught an adjacent visual regression that the implementing role introduced and
did not self-report. The observed cost was +10,199 tokens and +24.868 seconds.
It is one stochastic paired observation, not a completion-rate estimate. At
least two additional independent pairs under the unchanged r2 protocol are
required before using this task for the assignment's three-run key conclusion.
Machine-readable summaries and complete trajectories are in
`results/designbench/`.

## Benchmark limitation found

DesignBench's gold pages are static rendering references. They are not reliable
functional oracles for interactive requirements. In the pinned data, Edit 1's
gold page renders literal name placeholders rather than implementing input
state, and Edit 11's date-time field is always present rather than conditionally
revealed after a radio selection.

Accordingly, DesignBench is a secondary external static-edit check. The
project's controlled benchmark and hidden Playwright tests remain the basis for
claims about functional completion and regression preservation.
