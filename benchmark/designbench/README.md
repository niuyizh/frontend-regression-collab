# DesignBench React subset

This adapter pins five tasks from `WebPAI/DesignBench` at revision
`a1e58d66ecbf1f77848bc5529ee7bbbe33bc25ba`. Dataset downloads are separately
pinned to Hugging Face revision `a04022a331a8ad385dbbf26a1da9ca4a26a2628d`.
It downloads only the selected task assets from `whale99/DesignBench`; the
1.12 GB full dataset is not needed.

The upstream repository and downloaded data are ignored by Git. Set
`DESIGNBENCH_ROOT` to an existing checkout, or clone it into
`benchmark/designbench/upstream`.

```bash
git clone https://github.com/WebPAI/DesignBench.git benchmark/designbench/upstream
git -C benchmark/designbench/upstream checkout a1e58d66ecbf1f77848bc5529ee7bbbe33bc25ba
npm --prefix benchmark/designbench/upstream/web/my-react-app ci
python3 scripts/fetch_designbench_subset.py
python3 scripts/prepare_designbench.py db-e11 --force
npm --prefix runs/designbench/db-e11/initial run verify:agent
```

Print an OpenCollab run plan without calling the model API:

```bash
python3 scripts/run_designbench_experiment.py db-e11 dev-qa --repetition 1
```

Add `--execute --force` only when a paid run is intended. The current adapter
records agent output, render status, hidden DOM checks, a fixed-viewport
screenshot, pixel similarity, and normalized MAE similarity. Edit tasks pass
only when every structural check passes and MAE visual progress is at least
50% of the frozen initial-to-gold improvement. The Compile task passes when the
repaired page renders successfully.

Score an already prepared workspace without calling a model:

```bash
python3 scripts/score_designbench.py \
  db-e11 runs/designbench/db-e11/dev-qa/r1 \
  --output-dir results/designbench/manual/db-e11
```

Calibration values and the threshold are versioned in `scoring.json`. The
target screenshots remain outside ordinary agent workspaces.

The subset uses four Edit tasks in DesignBench's `code` mode and one Compile
task. A visually specified
Repair task was removed because the configured `deepseek-flash` endpoint does
not expose a vision-capable model; evaluating it through text-only prompts
would confound model input capability with the collaboration strategy.

DesignBench's checked-in gold pages are static rendering references, not
functional UI oracles. For example, Edit 1 renders literal name placeholders
and Edit 11 includes the date-time input without implementing the requested
conditional interaction. Consequently, this subset is a secondary static
edit/compile validation set. The project's own hidden Playwright tasks remain
the primary source of functional completion and regression results.

Use `--gold` only for harness validation. Gold code and target screenshots are
never copied into an ordinary agent workspace.
