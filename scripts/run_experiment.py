"""Prepare, run, and score one OpenCollab experiment condition."""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import time
from pathlib import Path
from typing import Any

from common import (
    PROJECT_ROOT,
    require_command,
    result_dir,
    run_id,
    task_prompt,
    task_record,
)
from evaluate_run import evaluate
from prepare_run import prepare

DEFAULT_OPENCOLLAB_ROOT = Path(
    os.environ.get("OPENCOLLAB_ROOT", PROJECT_ROOT.parent / "code-assistant" / "OpenCollab")
)


def _extract_json(text: str) -> dict[str, Any] | None:
    for start in reversed([match.start() for match in re.finditer(r"(?:^|\n)\{", text)]):
        if text[start] == "\n":
            start += 1
        try:
            value = json.JSONDecoder().raw_decode(text[start:])[0]
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and ("status" in value or "condition" in value):
            return value
    return None


def run_one(
    task_id: str,
    condition: str,
    repetition: int,
    *,
    opencollab_root: Path,
    execute: bool,
    force: bool,
) -> dict[str, Any]:
    task_record(task_id)
    require_command("node")
    require_command("npm")
    uv = require_command("uv")
    opencollab_root = opencollab_root.resolve()
    if not (opencollab_root / "pyproject.toml").exists():
        raise RuntimeError(f"invalid OpenCollab checkout: {opencollab_root}")

    workflow = "frontend-single" if condition == "single" else "frontend-dev-qa"
    workspace = PROJECT_ROOT / "runs" / task_id / condition / f"r{repetition}"
    command = [
        uv,
        "run",
        "opencollab",
        "workflow",
        "run",
        workflow,
        "--workspace",
        str(workspace.resolve()),
        "--task-file",
        str(task_prompt(task_id).resolve()),
        "--args",
        json.dumps({"allow_unisolated_shell": True}),
        "--budget",
        "36000",
        "--concurrency",
        "1",
        "--task-concurrency",
        "1",
        "--isolation",
        "shared",
        "--trace",
        "--save",
    ]
    plan = {
        "run_id": run_id(task_id, condition, repetition),
        "task_id": task_id,
        "condition": condition,
        "repetition": repetition,
        "workflow": workflow,
        "budget": 36_000,
        "workspace": str(workspace.resolve()),
        "command": command,
    }
    if not execute:
        return {"status": "dry-run", **plan}

    workspace = prepare(task_id, condition, repetition, force=force)
    output_dir = result_dir(task_id, condition, repetition)
    output_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["OPENCOLLAB_WORKFLOWS_DIR"] = str((PROJECT_ROOT / "workflows").resolve())
    env["OPENCOLLAB_THINKING"] = "false"
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=opencollab_root,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=1800,
    )
    agent_seconds = round(time.monotonic() - started, 3)
    (output_dir / "opencollab.log").write_text(completed.stdout, encoding="utf-8")
    parsed = _extract_json(completed.stdout)
    agent_record = {
        **plan,
        "returncode": completed.returncode,
        "agent_seconds": agent_seconds,
        "workflow_result": parsed,
    }
    (output_dir / "agent.json").write_text(
        json.dumps(agent_record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    retained_artifacts = workspace / ".opencollab"
    if retained_artifacts.is_dir():
        shutil.copytree(
            retained_artifacts,
            output_dir / "opencollab-artifacts",
            dirs_exist_ok=True,
        )
    evaluation = evaluate(task_id, condition, repetition)
    final_status = "completed" if evaluation["agent_run_valid"] else "invalid-agent-run"
    return {"status": final_status, "agent": agent_record, "evaluation": evaluation}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id")
    parser.add_argument("condition", choices=("single", "dev-qa"))
    parser.add_argument("--repetition", type=int, default=1)
    parser.add_argument("--opencollab-root", type=Path, default=DEFAULT_OPENCOLLAB_ROOT)
    parser.add_argument("--execute", action="store_true", help="make paid model calls")
    parser.add_argument("--force", action="store_true", help="replace this exact run workspace")
    args = parser.parse_args()
    result = run_one(
        args.task_id,
        args.condition,
        args.repetition,
        opencollab_root=args.opencollab_root,
        execute=args.execute,
        force=args.force,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
