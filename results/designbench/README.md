# DesignBench raw calibration results

This directory contains real `deepseek-flash` runs; no result is synthetic.

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
