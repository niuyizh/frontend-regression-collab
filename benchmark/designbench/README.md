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
records agent output and render success; task-specific functional and visual
scores are intentionally still marked unimplemented.

Use `--gold` only for harness validation. Gold code and target screenshots are
never copied into an ordinary agent workspace.
