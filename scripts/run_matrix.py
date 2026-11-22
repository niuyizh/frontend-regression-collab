"""Print or execute the preregistered 18-run comparison matrix."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from common import result_dir
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


def _has_recorded_result(task_id: str, condition: str, repetition: int) -> bool:
    output = result_dir(task_id, condition, repetition)
    return (output / "agent.json").is_file() and (output / "evaluation.json").is_file()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="execute paid model calls sequentially")
    parser.add_argument("--force", action="store_true")
    parser.add_argument(
        "--resume",
        action="store_true",
        help="skip runs that already have both agent and evaluation records",
    )
    parser.add_argument(
        "--keep-going",
        action="store_true",
        help="retain invalid runs and continue the remaining frozen matrix",
    )
    parser.add_argument("--opencollab-root", type=Path, default=DEFAULT_OPENCOLLAB_ROOT)
    args = parser.parse_args()
    results = []
    for task_id, condition, repetition in matrix():
        if args.execute and args.resume and _has_recorded_result(
            task_id, condition, repetition
        ):
            print(
                json.dumps(
                    {
                        "status": "skipped-recorded",
                        "run_id": f"{task_id}__{condition}__r{repetition}",
                    }
                )
            )
            continue
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
        if args.execute and result.get("status") != "completed" and not args.keep_going:
            break
    if not args.execute:
        print(f"planned_runs={len(results)}; add --execute only after the smoke gate passes")


if __name__ == "__main__":
    main()
