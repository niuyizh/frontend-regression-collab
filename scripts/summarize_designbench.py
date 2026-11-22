"""Aggregate the frozen DesignBench paired experiment from raw run artifacts."""

from __future__ import annotations

import argparse
import json
import statistics
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT

TASK_ID = "db-e30"
CONDITIONS = ("single", "dev-qa")
FROZEN_REPETITIONS = (2, 3, 4)


def _read_result(raw_root: Path, condition: str, repetition: int) -> dict[str, Any]:
    path = raw_root / f"{TASK_ID}__{condition}__r{repetition}" / "result.json"
    if not path.is_file():
        raise FileNotFoundError(f"missing frozen experiment result: {path}")
    result = json.loads(path.read_text(encoding="utf-8"))
    if result.get("condition") != condition or result.get("repetition") != repetition:
        raise ValueError(f"run identity mismatch in {path}")
    if result.get("task", {}).get("id") != TASK_ID:
        raise ValueError(f"task identity mismatch in {path}")
    return result


def _run_record(result: dict[str, Any]) -> dict[str, Any]:
    workflow = result.get("workflow_result") or {}
    evaluation = result.get("evaluation") or {}
    return {
        "run_id": result["run_id"],
        "condition": result["condition"],
        "repetition": result["repetition"],
        "agent_run_valid": bool(result.get("agent_run_valid")),
        "task_passed": bool(result.get("task_passed")),
        "tokens": workflow.get("tokens_spent"),
        "agent_seconds": result.get("agent_seconds"),
        "evaluation_seconds": evaluation.get("duration_seconds"),
        "visual_progress": evaluation.get("visual_progress"),
        "structural_passed": evaluation.get("structural_passed"),
        "qa_verdict": (workflow.get("qa") or {}).get("verdict"),
        "repair_triggered": workflow.get("repair") is not None,
        "developer_tokens": (workflow.get("developer_outcome") or {}).get("tokens"),
        "qa_tokens": (workflow.get("qa_outcome") or {}).get("tokens"),
        "repair_tokens": (workflow.get("repair_outcome") or {}).get("tokens"),
    }


def _distribution(values: list[float | int]) -> dict[str, float]:
    numeric = [float(value) for value in values]
    return {
        "mean": statistics.fmean(numeric),
        "sample_standard_deviation": statistics.stdev(numeric),
        "median": statistics.median(numeric),
        "minimum": min(numeric),
        "maximum": max(numeric),
    }


def _condition_summary(records: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "runs": len(records),
        "valid_runs": sum(record["agent_run_valid"] for record in records),
        "task_passes": sum(record["task_passed"] for record in records),
        "task_completion_rate": statistics.fmean(
            float(record["task_passed"]) for record in records
        ),
        "tokens": _distribution([record["tokens"] for record in records]),
        "agent_seconds": _distribution(
            [record["agent_seconds"] for record in records]
        ),
        "visual_progress": _distribution(
            [record["visual_progress"] for record in records]
        ),
        "qa_failures": sum(record["qa_verdict"] == "FAIL" for record in records),
        "repairs": sum(record["repair_triggered"] for record in records),
    }


def summarize(raw_root: Path) -> dict[str, Any]:
    records = [
        _run_record(_read_result(raw_root, condition, repetition))
        for repetition in FROZEN_REPETITIONS
        for condition in CONDITIONS
    ]
    invalid = [record["run_id"] for record in records if not record["agent_run_valid"]]
    if invalid:
        raise ValueError(f"frozen comparison contains invalid agent runs: {invalid}")

    by_condition = {
        condition: [record for record in records if record["condition"] == condition]
        for condition in CONDITIONS
    }
    paired = []
    for repetition in FROZEN_REPETITIONS:
        single = next(
            record
            for record in by_condition["single"]
            if record["repetition"] == repetition
        )
        dev_qa = next(
            record
            for record in by_condition["dev-qa"]
            if record["repetition"] == repetition
        )
        paired.append(
            {
                "repetition": repetition,
                "task_pass_delta": int(dev_qa["task_passed"])
                - int(single["task_passed"]),
                "token_delta": dev_qa["tokens"] - single["tokens"],
                "agent_seconds_delta": dev_qa["agent_seconds"]
                - single["agent_seconds"],
                "visual_progress_delta": dev_qa["visual_progress"]
                - single["visual_progress"],
            }
        )

    return {
        "schema_version": 2,
        "task": TASK_ID,
        "model": "deepseek-flash",
        "protocol": {
            "repetitions": list(FROZEN_REPETITIONS),
            "conditions": list(CONDITIONS),
            "global_budget_per_run": 48_000,
            "paired_runs": True,
            "agent_time_excludes_external_evaluator": True,
            "pilot_r1_excluded": True,
        },
        "runs": records,
        "conditions": {
            condition: _condition_summary(by_condition[condition])
            for condition in CONDITIONS
        },
        "paired_differences": {
            "runs": paired,
            "token_delta": _distribution([row["token_delta"] for row in paired]),
            "agent_seconds_delta": _distribution(
                [row["agent_seconds_delta"] for row in paired]
            ),
            "mean_task_pass_delta": statistics.fmean(
                row["task_pass_delta"] for row in paired
            ),
            "mean_visual_progress_delta": statistics.fmean(
                row["visual_progress_delta"] for row in paired
            ),
        },
        "mechanism_observation": {
            "qa_failures": sum(
                record["qa_verdict"] == "FAIL" for record in by_condition["dev-qa"]
            ),
            "repairs_triggered": sum(
                record["repair_triggered"] for record in by_condition["dev-qa"]
            ),
            "description": (
                "In r2 QA identified an unrelated p-4 to p-2 toolbar-padding change; "
                "the repair restored p-4 and the final candidate passed. QA returned "
                "PASS without repair in r3 and r4."
            ),
        },
        "claim_boundary": (
            "Three repetitions support a task-specific robustness result, not a "
            "general completion-rate claim across frontend tasks."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--raw-root",
        type=Path,
        default=PROJECT_ROOT / "results" / "designbench" / "raw",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=PROJECT_ROOT / "results" / "designbench" / "summary.json",
    )
    args = parser.parse_args()
    summary = summarize(args.raw_root)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(summary['runs'])} frozen runs to {args.output}")


if __name__ == "__main__":
    main()
