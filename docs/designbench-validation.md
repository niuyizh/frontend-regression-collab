# DesignBench adapter validation

## Scope decision

The selected DeepSeek endpoint exposed only `deepseek-flash` and
`deepseek-v4-pro` through `/models` on 2026-11-22; neither identifier indicates
vision support. OpenCollab's workflow API also cannot currently pass structured
image content to `agent_run()`. The external subset therefore uses
DesignBench's text-and-code (`code`) mode: four React Edit tasks and one Compile
task. The screenshot-dependent Repair task was removed.

## Frozen tasks

All five tasks below were used to calibrate initial/gold behavior and the
external scorer. `db-e30` has three post-pilot paired repetitions. The other
four later received one Single and one artifact-first Dev-QA real-Agent run
each; those one-repetition results are descriptive failure-mode evidence, not
part of the repeated comparison.

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

## Three-run paired result

The post-pilot r2-r4 pairs used the same `deepseek-flash` endpoint, task prompt,
48k global cap, initial workspace, and scorer. Time below is OpenCollab agent
wall time and excludes the external evaluator. Values are mean ± sample SD.

| Condition | Valid | Task pass | Tokens | Time (s) | Mean visual progress |
|---|---:|---:|---:|---:|---:|
| Single | 3/3 | 2/3 | 13,157 ± 1,854 | 21.346 ± 4.004 | 0.633 |
| Dev-QA | 3/3 | 3/3 | 19,313 ± 4,520 | 32.577 ± 15.852 | 0.798 |

Single preserved the outer `p-4`, but added unrequested blur, transparency,
`z-10`, and fixed button sizing. Its structural checks passed, while its visual
progress remained below the frozen 0.5 threshold. In Dev-QA, the first
Developer instead changed outer toolbar padding from `p-4` to `p-2`; the public
render smoke still passed. Regression QA cited that exact diff as a violation
of “Nothing else should change,” and the repair restored `p-4`. The final page
passed all structural checks and reached 0.798 visual progress.

The r2 pair demonstrates the intended mechanism: an independent diff-only role
caught an adjacent visual regression that the implementing role introduced and
did not self-report. The observed cost was +10,199 tokens and +24.868 seconds.
In r3 and r4, QA returned PASS and did not trigger a repair. Across all three
pairs, Dev-QA increased task completion by 33.3 percentage points while using
6,156 more tokens and 11.230 more seconds on average. This is a task-specific
robustness result, not a general frontend completion-rate estimate.
Machine-readable summaries and complete trajectories are in
`results/designbench/`.

## Benchmark limitation found

DesignBench's gold pages are static rendering references. They are not reliable
functional oracles for interactive requirements. In the pinned data, Edit 1's
gold page renders literal name placeholders rather than implementing input
state, and Edit 11's date-time field is always present rather than conditionally
revealed after a radio selection.

The four-task real-Agent pilot exposed an additional adapter measurement flaw
in `db-e11`: the hidden checker accepts only the unspecified implementation
value `specificTime`, although agents reasonably used `specific-time`; it also
checks for the conditional date-time input before selecting that radio. Thus a
semantically correct implementation can fail the current structural oracle.
The original outputs are retained unchanged rather than rescored mid-pilot.

Accordingly, DesignBench is a secondary external static-edit check. The
project's controlled benchmark and hidden Playwright tests remain the basis for
claims about functional completion and regression preservation.
