"""Create one clean, committed task workspace from the fixed frontend fixture."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
from pathlib import Path

from common import (
    BASE_APP,
    PROJECT_ROOT,
    require_command,
    run_id,
    run_workspace,
    sha256_file,
    task_prompt,
    task_record,
)

CONDITIONS = ("single", "dev-qa", "dev-qa-resilient")


def prepare(task_id: str, condition: str, repetition: int, *, force: bool = False) -> Path:
    task = task_record(task_id)
    if condition not in CONDITIONS:
        raise ValueError(f"condition must be one of {CONDITIONS}")
    if repetition < 1:
        raise ValueError("repetition must be positive")
    require_command("git")
    require_command("node")
    require_command("npm")

    target = run_workspace(task_id, condition, repetition).resolve()
    runs_root = (PROJECT_ROOT / "runs").resolve()
    if not target.is_relative_to(runs_root):
        raise RuntimeError("refusing to prepare a workspace outside runs/")
    if target.exists():
        if not force:
            raise FileExistsError(f"workspace already exists: {target}; pass --force to replace it")
        shutil.rmtree(target)

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        BASE_APP,
        target,
        ignore=shutil.ignore_patterns(
            "node_modules", "dist", "test-results", "playwright-report", "hidden-results.json"
        ),
    )
    dependencies = PROJECT_ROOT / "node_modules"
    if not dependencies.is_dir():
        raise RuntimeError("project node_modules is missing; run npm install in the project root")
    (target / "node_modules").symlink_to(dependencies, target_is_directory=True)

    prompt = task_prompt(task_id)
    shutil.copy2(prompt, target / "TASK.md")
    manifest = {
        "schema_version": 1,
        "run_id": run_id(task_id, condition, repetition),
        "task": task,
        "condition": condition,
        "repetition": repetition,
        "task_prompt_sha256": sha256_file(prompt),
        "base_app": "benchmark/base-app",
    }
    (target / "run-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    commands = [
        ["git", "init", "-q"],
        ["git", "config", "user.name", "Frontend Regression Harness"],
        ["git", "config", "user.email", "harness@example.invalid"],
        ["git", "add", "."],
        ["git", "commit", "-q", "-m", "fixture: clean task workspace"],
    ]
    for command in commands:
        subprocess.run(command, cwd=target, check=True)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id")
    parser.add_argument("condition", choices=CONDITIONS)
    parser.add_argument("--repetition", type=int, default=1)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    print(prepare(args.task_id, args.condition, args.repetition, force=args.force))


if __name__ == "__main__":
    main()
