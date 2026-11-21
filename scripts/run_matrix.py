"""Print or execute the preregistered 18-run comparison matrix."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from run_experiment import DEFAULT_OPENCOLLAB_ROOT, run_one

ALL_TASKS = ("t01-search", "t02-modal-priority", "t03-sync-retry", "t04-responsive-nav", "t05-form-due-date")
KEY_TASKS = ("t03-sync-retry", "t04-responsive-nav")
CONDITIONS = ("single", "dev-qa")
ORDER_SEED = 20261120


def matrix() -> list[tuple[str, str, int]]:
    runs = [(task, condition, 1) for task in ALL_TASKS for condition in CONDITIONS]
    runs.extend(
        (task, condition, repetition)
        for task in KEY_TASKS
        for condition in CONDITIONS
        for repetition in (2, 3)
    )
    random.Random(ORDER_SEED).shuffle(runs)
    return runs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="execute paid model calls sequentially")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--opencollab-root", type=Path, default=DEFAULT_OPENCOLLAB_ROOT)
    args = parser.parse_args()
    if args.execute:
        raise SystemExit(
            "formal matrix is suspended: the 16k calibration run stopped before implementation; "
            "revise and preregister equal budgets before enabling paid matrix execution"
        )
    results = []
    for task_id, condition, repetition in matrix():
        result = run_one(
            task_id,
            condition,
            repetition,
            opencollab_root=args.opencollab_root,
            execute=args.execute,
            force=args.force,
        )
        results.append(result)
        print(json.dumps(result, ensure_ascii=False))
        if args.execute and result.get("status") != "completed":
            break
    if not args.execute:
        print(f"planned_runs={len(results)}; add --execute only after the smoke gate passes")


if __name__ == "__main__":
    main()
