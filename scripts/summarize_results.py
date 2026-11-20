"""Aggregate real run artifacts without filling missing experiments."""

from __future__ import annotations

import csv
import json
from typing import Any

from common import PROJECT_ROOT, RAW_RESULTS_DIR


def rows() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for evaluation_path in sorted(RAW_RESULTS_DIR.glob("*/evaluation.json")):
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        agent_path = evaluation_path.with_name("agent.json")
        agent = json.loads(agent_path.read_text(encoding="utf-8")) if agent_path.exists() else {}
        workflow = agent.get("workflow_result") or {}
        records.append(
            {
                "run_id": evaluation["run_id"],
                "task_id": evaluation["task_id"],
                "condition": evaluation["condition"],
                "repetition": evaluation["repetition"],
                "task_complete": evaluation["task_complete"],
                "build_passed": evaluation["build_passed"],
                "public_regression_passed": evaluation["public_regression_passed"],
                "hidden_passed": evaluation["hidden"]["passed"],
                "hidden_expected": evaluation["hidden"]["expected"],
                "test_tampering": evaluation["test_tampering"],
                "agent_seconds": agent.get("agent_seconds"),
                "evaluation_seconds": evaluation["evaluation_seconds"],
                "tokens": workflow.get("tokens_spent") if isinstance(workflow, dict) else None,
            }
        )
    return records


def main() -> None:
    records = rows()
    output_csv = PROJECT_ROOT / "results" / "runs.csv"
    output_json = PROJECT_ROOT / "results" / "summary.json"
    fields = [
        "run_id", "task_id", "condition", "repetition", "task_complete", "build_passed",
        "public_regression_passed", "hidden_passed", "hidden_expected", "test_tampering",
        "agent_seconds", "evaluation_seconds", "tokens",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(records)
    conditions: dict[str, dict[str, Any]] = {}
    for condition in ("single", "dev-qa"):
        subset = [row for row in records if row["condition"] == condition]
        conditions[condition] = {
            "completed_runs": len(subset),
            "task_completion_rate": (
                sum(bool(row["task_complete"]) for row in subset) / len(subset) if subset else None
            ),
            "mean_tokens": (
                sum(row["tokens"] for row in subset if isinstance(row["tokens"], int))
                / len([row for row in subset if isinstance(row["tokens"], int)])
                if any(isinstance(row["tokens"], int) for row in subset)
                else None
            ),
            "mean_agent_seconds": (
                sum(row["agent_seconds"] for row in subset if isinstance(row["agent_seconds"], (int, float)))
                / len([row for row in subset if isinstance(row["agent_seconds"], (int, float))])
                if any(isinstance(row["agent_seconds"], (int, float)) for row in subset)
                else None
            ),
        }
    output_json.write_text(
        json.dumps({"runs": len(records), "conditions": conditions}, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(records)} real runs to {output_csv} and {output_json}")


if __name__ == "__main__":
    main()
