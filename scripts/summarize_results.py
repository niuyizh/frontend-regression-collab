"""Aggregate real run artifacts without filling missing experiments."""

from __future__ import annotations

import csv
import json
import statistics
from typing import Any

from common import PROJECT_ROOT, RAW_RESULTS_DIR


def rows() -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for evaluation_path in sorted(RAW_RESULTS_DIR.glob("*/evaluation.json")):
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        agent_path = evaluation_path.with_name("agent.json")
        agent = json.loads(agent_path.read_text(encoding="utf-8")) if agent_path.exists() else {}
        workflow = agent.get("workflow_result") or {}
        developer_outcome = workflow.get("developer_outcome") or {}
        qa_outcome = workflow.get("qa_outcome") or {}
        repair_outcome = workflow.get("repair_outcome") or {}
        handoff_recovery = workflow.get("handoff_recovery") or {}
        qa = workflow.get("qa") or {}
        hidden_passed = evaluation["hidden"]["passed"]
        hidden_expected = evaluation["hidden"]["expected"]
        records.append(
            {
                "run_id": evaluation["run_id"],
                "task_id": evaluation["task_id"],
                "condition": evaluation["condition"],
                "repetition": evaluation["repetition"],
                "task_complete": evaluation["task_complete"],
                "agent_run_valid": evaluation.get("agent_run_valid"),
                "build_passed": evaluation["build_passed"],
                "public_regression_passed": evaluation["public_regression_passed"],
                "hidden_passed": hidden_passed,
                "hidden_expected": hidden_expected,
                "test_tampering": evaluation["test_tampering"],
                "agent_seconds": agent.get("agent_seconds"),
                "evaluation_seconds": evaluation["evaluation_seconds"],
                "tokens": workflow.get("tokens_spent") if isinstance(workflow, dict) else None,
                "workflow_status": workflow.get("status"),
                "developer_status": developer_outcome.get("status"),
                "qa_status": qa_outcome.get("status"),
                "qa_verdict": qa.get("verdict"),
                "repair_status": repair_outcome.get("status"),
                "developer_recovered": bool(handoff_recovery.get("developer")),
                "repair_recovered": bool(handoff_recovery.get("repair")),
                "external_checks_passed": bool(
                    evaluation["build_passed"]
                    and evaluation["public_regression_passed"]
                    and hidden_passed == hidden_expected
                    and not evaluation["test_tampering"]
                ),
                "failure_reason": workflow.get("error"),
            }
        )
    return records


def distribution(values: list[int | float]) -> dict[str, int | float | None]:
    return {
        "n": len(values),
        "mean": statistics.mean(values) if values else None,
        "sample_sd": statistics.stdev(values) if len(values) > 1 else None,
        "median": statistics.median(values) if values else None,
        "min": min(values) if values else None,
        "max": max(values) if values else None,
    }


def condition_summary(subset: list[dict[str, Any]]) -> dict[str, Any]:
    completed = sum(bool(row["task_complete"]) for row in subset)
    externally_passing = sum(bool(row["external_checks_passed"]) for row in subset)
    tokens = [row["tokens"] for row in subset if isinstance(row["tokens"], int)]
    seconds = [
        row["agent_seconds"]
        for row in subset
        if isinstance(row["agent_seconds"], (int, float))
    ]
    return {
        "runs": len(subset),
        "task_complete_count": completed,
        "task_completion_rate": completed / len(subset) if subset else None,
        "external_checks_passed_count": externally_passing,
        "external_checks_passed_rate": externally_passing / len(subset) if subset else None,
        "invalid_agent_runs": sum(not bool(row["agent_run_valid"]) for row in subset),
        "tokens": distribution(tokens),
        "agent_seconds": distribution(seconds),
        "qa_fail_verdicts": sum(row["qa_verdict"] == "FAIL" for row in subset),
        "developer_handoffs_recovered": sum(bool(row["developer_recovered"]) for row in subset),
        "repair_handoffs_recovered": sum(bool(row["repair_recovered"]) for row in subset),
    }


def main() -> None:
    records = rows()
    output_csv = PROJECT_ROOT / "results" / "runs.csv"
    output_json = PROJECT_ROOT / "results" / "summary.json"
    fields = [
        "run_id", "task_id", "condition", "repetition", "task_complete", "agent_run_valid", "build_passed",
        "public_regression_passed", "hidden_passed", "hidden_expected", "test_tampering",
        "agent_seconds", "evaluation_seconds", "tokens", "workflow_status",
        "developer_status", "qa_status", "qa_verdict", "repair_status",
        "developer_recovered", "repair_recovered", "external_checks_passed", "failure_reason",
    ]
    with output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(records)
    conditions: dict[str, dict[str, Any]] = {}
    for condition in sorted({row["condition"] for row in records}):
        subset = [row for row in records if row["condition"] == condition]
        conditions[condition] = condition_summary(subset)
    per_task: dict[str, list[dict[str, Any]]] = {}
    for task_id in sorted({row["task_id"] for row in records}):
        per_task[task_id] = [
            {
                key: row[key]
                for key in (
                    "condition", "repetition", "task_complete", "agent_run_valid",
                    "external_checks_passed", "tokens", "agent_seconds", "qa_verdict",
                    "developer_recovered", "repair_recovered", "failure_reason",
                )
            }
            for row in records
            if row["task_id"] == task_id
        ]
    output_json.write_text(
        json.dumps(
            {"schema_version": 2, "runs": len(records), "conditions": conditions, "per_task": per_task},
            indent=2,
        ) + "\n",
        encoding="utf-8",
    )
    print(f"wrote {len(records)} real runs to {output_csv} and {output_json}")


if __name__ == "__main__":
    main()
