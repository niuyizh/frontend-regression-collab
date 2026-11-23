"""Summarize the one-repetition DesignBench four-task pilot."""

from __future__ import annotations

import json
from statistics import mean
from typing import Any

from common import PROJECT_ROOT


TASKS = ("db-e01", "db-e11", "db-e27", "db-c06")
CONDITIONS = ("single", "dev-qa-resilient")
RAW_ROOT = PROJECT_ROOT / "results" / "designbench" / "raw"
OUTPUT = PROJECT_ROOT / "results" / "designbench" / "four-task-pilot.json"


def summarize() -> dict[str, Any]:
    runs = []
    for task in TASKS:
        for condition in CONDITIONS:
            run_id = f"{task}__{condition}__r1"
            record = json.loads((RAW_ROOT / run_id / "result.json").read_text(encoding="utf-8"))
            workflow = record.get("workflow_result") or {}
            evaluation = record.get("evaluation") or {}
            visual = evaluation.get("visual") or {}
            runs.append(
                {
                    "run_id": run_id,
                    "task": task,
                    "condition": condition,
                    "agent_run_valid": record["agent_run_valid"],
                    "task_passed": record["task_passed"],
                    "agent_seconds": record["agent_seconds"],
                    "tokens": workflow.get("tokens_spent"),
                    "developer_status": (workflow.get("developer_outcome") or {}).get("status"),
                    "qa_status": (workflow.get("qa_outcome") or {}).get("status"),
                    "qa_verdict": (workflow.get("qa") or {}).get("verdict"),
                    "repair_status": (workflow.get("repair_outcome") or {}).get("status"),
                    "render_passed": evaluation.get("render_passed"),
                    "structural_passed": evaluation.get("structural_passed"),
                    "visual_progress": evaluation.get("visual_progress"),
                    "checks": visual.get("checks"),
                }
            )

    conditions = {}
    for condition in CONDITIONS:
        selected = [run for run in runs if run["condition"] == condition]
        conditions[condition] = {
            "runs": len(selected),
            "agent_valid": sum(run["agent_run_valid"] for run in selected),
            "task_passed": sum(run["task_passed"] for run in selected),
            "mean_tokens": mean(run["tokens"] for run in selected),
            "mean_agent_seconds": mean(run["agent_seconds"] for run in selected),
        }
    return {
        "schema_version": 1,
        "scope": "one-repetition pilot; descriptive only",
        "model": "deepseek-flash",
        "global_budget_per_run": 48_000,
        "tasks": list(TASKS),
        "conditions": conditions,
        "runs": runs,
        "known_measurement_limits": [
            "db-e01 only recognizes a heading present in the default empty-name DOM",
            "db-e11 hard-codes radio value specificTime and checks the conditional datetime input without selecting it",
            "Edit-task visual progress rewards similarity to one static upstream target",
        ],
    }


def main() -> None:
    OUTPUT.write_text(
        json.dumps(summarize(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()
