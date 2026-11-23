# DesignBench raw calibration results

This directory contains real `deepseek-flash` runs; no result is synthetic.

## Four-task real-Agent pilot

The four tasks that previously had only adapter calibration now each have one
Single run and one artifact-first Dev-QA run under the same 48k global cap.
This is a descriptive pilot, not a repeated statistical result.

| Task | Single | Dev-QA resilient | Key observation |
|---|---:|---:|---|
| `db-e01` | FAIL, 18,638 tok | FAIL, 18,991 tok | Both implemented the name split; empty-state DOM and visual progress affected scoring. |
| `db-e11` | FAIL, 30,786 tok | FAIL, 27,404 tok | Both implemented the interaction; the scorer hard-codes an unspecified radio value and checks a conditional field before clicking. |
| `db-e27` | FAIL, 34,720 tok | FAIL, 29,195 tok | Single passed all six structural checks; Dev-QA stopped with an incomplete edit. |
| `db-c06` | PASS, 9,069 tok | PASS, 12,695 tok | Both made the same one-line fix; QA added cost without outcome gain. |

Single produced 4/4 valid runs and 1/4 final passes (mean 23,303 tokens,
13.40s). Dev-QA resilient produced 3/4 valid runs and 1/4 final passes (mean
22,071 tokens, 20.31s). The lower Dev-QA token mean is not an efficiency gain:
its most complex run stopped incomplete.

Machine-readable summary: [`four-task-pilot.json`](four-task-pilot.json).
Full raw results and OpenCollab sessions are stored under `raw/<run-id>/`.
Two strict-workflow calibration artifacts are retained but excluded from this
pair: `db-e01__dev-qa__r1` completed, while `db-e11__dev-qa__r1` stopped after
the Developer exhausted its role budget before QA. That failure motivated using
the already validated artifact-first condition consistently in the pilot.

- `raw/db-e30__*__r1/`: retained pilot. Single completed but made unrelated
  changes; Dev-QA stopped after its Developer edit and smoke verification
  because the 30k role budget could not reserve another full-context call.
- `rescored-v2/`: r1 candidates plus frozen initial/gold rescored after removing
  a DOM-wrapper-specific structural assumption. These files do not alter the
  original r1 artifacts.
- `raw/db-e30__*__r2..r4/`: three valid paired comparisons under the same
  bounded-read prompt and revised scorer. Single passed 2/3; Dev-QA passed 3/3.
  In r2, Dev-QA detected and repaired an unrelated toolbar-padding change.
- `summary.json`: compact values used by the project documentation.

Each raw run contains the OpenCollab log, saved session/orchestration records,
workflow result, evaluator log, fixed-viewport screenshot, pixel diff, and
machine-readable score. API credentials are not stored in these artifacts.

The r1 and r2 protocols differ, so r1 is not pooled with r2-r4. The three
post-pilot pairs use the same protocol and are the assignment's repeated
task-specific external validation.
