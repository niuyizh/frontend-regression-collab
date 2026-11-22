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

## Benchmark limitation found

DesignBench's gold pages are static rendering references. They are not reliable
functional oracles for interactive requirements. In the pinned data, Edit 1's
gold page renders literal name placeholders rather than implementing input
state, and Edit 11's date-time field is always present rather than conditionally
revealed after a radio selection.

Accordingly, DesignBench is a secondary external static-edit check. The
project's controlled benchmark and hidden Playwright tests remain the basis for
claims about functional completion and regression preservation.
