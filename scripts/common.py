"""Shared, deterministic paths and subprocess helpers for the experiment harness."""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BASE_APP = PROJECT_ROOT / "benchmark" / "base-app"
TASKS_DIR = PROJECT_ROOT / "tasks"
RUNS_DIR = PROJECT_ROOT / "runs"
RAW_RESULTS_DIR = PROJECT_ROOT / "results" / "raw"


def task_record(task_id: str) -> dict[str, Any]:
    data = json.loads((TASKS_DIR / "manifest.json").read_text(encoding="utf-8"))
    for item in data["tasks"]:
        if item["id"] == task_id:
            return item
    choices = ", ".join(item["id"] for item in data["tasks"])
    raise ValueError(f"unknown task {task_id!r}; choose one of: {choices}")


def task_prompt(task_id: str) -> Path:
    record = task_record(task_id)
    return TASKS_DIR / record["prompt_file"]


def run_id(task_id: str, condition: str, repetition: int) -> str:
    return f"{task_id}__{condition}__r{repetition}"


def run_workspace(task_id: str, condition: str, repetition: int) -> Path:
    return RUNS_DIR / task_id / condition / f"r{repetition}"


def result_dir(task_id: str, condition: str, repetition: int) -> Path:
    return RAW_RESULTS_DIR / run_id(task_id, condition, repetition)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def run_command(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 1200,
) -> dict[str, Any]:
    started = time.monotonic()
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=timeout,
        check=False,
    )
    return {
        "command": command,
        "cwd": str(cwd),
        "returncode": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
        "output": completed.stdout,
    }


def require_command(name: str) -> str:
    from shutil import which

    resolved = which(name)
    if not resolved:
        raise RuntimeError(
            f"required command {name!r} is not on PATH; activate the node22 Conda environment"
        )
    return resolved


def base_environment() -> dict[str, str]:
    env = os.environ.copy()
    env["PLAYWRIGHT_HTML_OPEN"] = "never"
    return env

