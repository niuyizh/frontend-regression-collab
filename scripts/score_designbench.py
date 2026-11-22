"""Score one prepared DesignBench workspace without exposing reference assets."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
from pathlib import Path
from typing import Any

from common import require_command
from prepare_designbench import ADAPTER_ROOT, DATA_ROOT, _task

SCORING_PATH = ADAPTER_ROOT / "scoring.json"


def _last_json_object(output: str) -> dict[str, Any] | None:
    for line in reversed(output.splitlines()):
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            return value
    return None


def _progress(value: float, initial: float, gold: float) -> float:
    if gold <= initial:
        raise ValueError("invalid calibration: gold must score above initial")
    return (value - initial) / (gold - initial)


def _target_image(task: dict[str, Any]) -> Path:
    task_dir = DATA_ROOT / task["kind"] / "react" / str(task["source_id"])
    metadata = json.loads(
        (task_dir / f"{task['source_id']}.json").read_text(encoding="utf-8-sig")
    )
    return (task_dir / f"{metadata['dst_id']}.png").resolve()


def score(
    task_id: str,
    workspace: Path,
    output_dir: Path,
    *,
    port: int = 4673,
) -> dict[str, Any]:
    require_command("node")
    require_command("npm")
    workspace = workspace.resolve()
    output_dir = output_dir.resolve()
    if not (workspace / "run-manifest.json").is_file():
        raise RuntimeError(f"not a prepared DesignBench workspace: {workspace}")
    run_manifest = json.loads(
        (workspace / "run-manifest.json").read_text(encoding="utf-8")
    )
    if run_manifest["task"]["id"] != task_id:
        raise ValueError("workspace task does not match requested task")
    if run_manifest.get("variant") == "gold":
        # Gold is valid for scorer calibration but cannot masquerade as an agent run.
        scoring_role = "calibration"
    else:
        scoring_role = "candidate"
    task = _task(task_id)
    output_dir.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["NEXT_TELEMETRY_DISABLED"] = "1"
    started = time.monotonic()

    visual: dict[str, Any] | None = None
    if task["kind"] == "edit":
        target = _target_image(task)
        command = [
            "node",
            str(ADAPTER_ROOT / "visual-score.mjs"),
            "--task",
            task_id,
            "--workspace",
            str(workspace),
            "--target",
            str(target),
            "--output",
            str(output_dir),
            "--port",
            str(port),
        ]
    else:
        command = ["npm", "run", "verify:agent"]
    completed = subprocess.run(
        command,
        cwd=workspace,
        env=env,
        text=True,
        encoding="utf-8",
        errors="replace",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
        timeout=120,
    )
    (output_dir / "scorer.log").write_text(completed.stdout, encoding="utf-8")
    render_passed = completed.returncode == 0

    visual_progress = None
    threshold = None
    structural_passed = None
    if task["kind"] == "edit" and render_passed:
        visual = _last_json_object(completed.stdout)
        if visual is None:
            render_passed = False
        else:
            scoring = json.loads(SCORING_PATH.read_text(encoding="utf-8"))
            calibration = scoring["calibration"][task_id]
            metric = scoring["metric"]
            visual_progress = _progress(
                float(visual[metric]),
                float(calibration["initial"][metric]),
                float(calibration["gold"][metric]),
            )
            threshold = float(scoring["minimum_visual_progress"])
            structural_passed = bool(visual["structural_passed"])

    if task["kind"] == "edit":
        passed = bool(
            render_passed
            and structural_passed
            and visual_progress is not None
            and threshold is not None
            and visual_progress >= threshold
        )
    else:
        passed = render_passed
    result = {
        "schema_version": 1,
        "task_id": task_id,
        "task_kind": task["kind"],
        "workspace": str(workspace),
        "scoring_role": scoring_role,
        "render_passed": render_passed,
        "structural_passed": structural_passed,
        "visual_progress": visual_progress,
        "minimum_visual_progress": threshold,
        "passed": passed,
        "returncode": completed.returncode,
        "duration_seconds": round(time.monotonic() - started, 3),
        "visual": visual,
    }
    (output_dir / "result.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id")
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--port", type=int, default=4673)
    args = parser.parse_args()
    print(
        json.dumps(
            score(args.task_id, args.workspace, args.output_dir, port=args.port),
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
