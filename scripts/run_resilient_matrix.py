"""Print or execute the frozen nine-run artifact-first Dev-QA matrix."""

from __future__ import annotations

import argparse
import json
import random
from pathlib import Path

from common import result_dir
from run_experiment import DEFAULT_OPENCOLLAB_ROOT, run_one
from run_matrix import ALL_TASKS, KEY_TASKS

CONDITION = "dev-qa-resilient"
ORDER_SEED = 20261122


def matrix() -> list[tuple[str, str, int]]:
    runs = [(task, CONDITION, 1) for task in ALL_TASKS]
    runs.extend(
        (task, CONDITION, repetition)
        for task in KEY_TASKS
        for repetition in (2, 3)
    )
    random.Random(ORDER_SEED).shuffle(runs)
    return runs


def _has_recorded_result(task_id: str, repetition: int) -> bool:
    output = result_dir(task_id, CONDITION, repetition)
    return (output / "agent.json").is_file() and (output / "evaluation.json").is_file()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--execute", action="store_true", help="execute paid calls sequentially")
    parser.add_argument("--resume", action="store_true", help="skip fully recorded runs")
    parser.add_argument("--keep-going", action="store_true", help="retain invalid runs and continue")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--opencollab-root", type=Path, default=DEFAULT_OPENCOLLAB_ROOT)
    args = parser.parse_args()

    completed = 0
    for task_id, condition, repetition in matrix():
        if args.execute and args.resume and _has_recorded_result(task_id, repetition):
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
        completed += 1
        print(json.dumps(result, ensure_ascii=False))
        if args.execute and result.get("status") != "completed" and not args.keep_going:
            break
    if not args.execute:
        print(f"planned_runs={completed}; add --execute only after freezing this protocol")


if __name__ == "__main__":
    main()
