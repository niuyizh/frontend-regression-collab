"""Evaluate one completed workspace with build, public regression, and hidden tests."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import Any

from common import (
    PROJECT_ROOT,
    base_environment,
    require_command,
    result_dir,
    run_command,
    run_id,
    run_workspace,
    task_record,
)


def _hidden_counts(report_path: Path) -> dict[str, int]:
    if not report_path.exists():
        return {"expected": 0, "passed": 0, "failed": 0, "skipped": 0}
    report = json.loads(report_path.read_text(encoding="utf-8"))
    counts = {"expected": 0, "passed": 0, "failed": 0, "skipped": 0}
    def suites(items: list[dict[str, Any]]):
        for suite in items:
            yield suite
            yield from suites(suite.get("suites", []))

    for suite in suites(report.get("suites", [])):
        for spec in suite.get("specs", []):
            for test in spec.get("tests", []):
                counts["expected"] += 1
                status = test.get("status")
                if status == "expected":
                    counts["passed"] += 1
                elif status == "skipped":
                    counts["skipped"] += 1
                else:
                    counts["failed"] += 1
    return counts


def _changed_paths(workspace: Path) -> list[str]:
    output = subprocess.run(
        ["git", "status", "--short"],
        cwd=workspace,
        text=True,
        encoding="utf-8",
        stdout=subprocess.PIPE,
        check=True,
    ).stdout
    return [line[3:] for line in output.splitlines() if len(line) >= 4]


def evaluate(task_id: str, condition: str, repetition: int) -> dict[str, Any]:
    task = task_record(task_id)
    workspace = run_workspace(task_id, condition, repetition).resolve()
    if not (workspace / ".git").exists():
        raise RuntimeError(f"prepared run workspace not found: {workspace}")
    require_command("node")
    require_command("npm")
    require_command("npx")

    output_dir = result_dir(task_id, condition, repetition)
    output_dir.mkdir(parents=True, exist_ok=True)
    env = base_environment()

    build = run_command(["npm", "run", "build"], cwd=workspace, env=env, timeout=180)
    public = run_command(["npm", "run", "test:public"], cwd=workspace, env=env, timeout=240)

    hidden_report = workspace / "hidden-results.json"
    if hidden_report.exists():
        hidden_report.unlink()
    hidden_env = env.copy()
    hidden_env.update(
        {
            "FRONTEND_WORKSPACE": str(workspace),
            "FRONTEND_TASK_ID": task_id,
            "FRONTEND_EVAL_PORT": str(4300 + (repetition % 100) * 10 + int(task_id[1:3])),
        }
    )
    hidden = run_command(
        ["npx", "playwright", "test", "--config", "evaluator/playwright.config.ts"],
        cwd=PROJECT_ROOT,
        env=hidden_env,
        timeout=240,
    )
    hidden_counts = _hidden_counts(hidden_report)
    changed = _changed_paths(workspace)
    test_tampering = any(
        path.startswith("tests/") or path in {"playwright.config.ts", "package.json"}
        for path in changed
    )
    agent_path = output_dir / "agent.json"
    agent_valid: bool | None = None
    if agent_path.exists():
        agent_record = json.loads(agent_path.read_text(encoding="utf-8"))
        workflow_result = agent_record.get("workflow_result")
        agent_valid = bool(
            agent_record.get("returncode") == 0
            and isinstance(workflow_result, dict)
            and workflow_result.get("status") == "ok"
            and isinstance(workflow_result.get("developer"), str)
            and bool(workflow_result.get("developer", "").strip())
            and (
                condition == "single"
                or isinstance(workflow_result.get("qa"), dict)
            )
        )
    complete = (
        build["returncode"] == 0
        and public["returncode"] == 0
        and hidden["returncode"] == 0
        and hidden_counts["passed"] == task["hidden_tests"]
        and not test_tampering
        and agent_valid is not False
    )
    result = {
        "schema_version": 1,
        "run_id": run_id(task_id, condition, repetition),
        "task_id": task_id,
        "condition": condition,
        "repetition": repetition,
        "task_complete": complete,
        "agent_run_valid": agent_valid,
        "build_passed": build["returncode"] == 0,
        "public_regression_passed": public["returncode"] == 0,
        "hidden": hidden_counts,
        "hidden_passed": hidden["returncode"] == 0,
        "test_tampering": test_tampering,
        "changed_paths": changed,
        "evaluation_seconds": round(
            build["duration_seconds"] + public["duration_seconds"] + hidden["duration_seconds"], 3
        ),
        "commands": {
            "build": {key: value for key, value in build.items() if key != "output"},
            "public": {key: value for key, value in public.items() if key != "output"},
            "hidden": {key: value for key, value in hidden.items() if key != "output"},
        },
    }
    (output_dir / "build.log").write_text(build["output"], encoding="utf-8")
    (output_dir / "public-tests.log").write_text(public["output"], encoding="utf-8")
    (output_dir / "hidden-tests.log").write_text(hidden["output"], encoding="utf-8")
    (output_dir / "evaluation.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if hidden_report.exists():
        (output_dir / "hidden-results.json").write_bytes(hidden_report.read_bytes())
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id")
    parser.add_argument("condition", choices=("single", "dev-qa", "dev-qa-resilient"))
    parser.add_argument("--repetition", type=int, default=1)
    args = parser.parse_args()
    print(json.dumps(evaluate(args.task_id, args.condition, args.repetition), indent=2))


if __name__ == "__main__":
    main()
