"""Prepare a clean DesignBench React workspace without Docker."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from common import PROJECT_ROOT, require_command

ADAPTER_ROOT = PROJECT_ROOT / "benchmark" / "designbench"
DATA_ROOT = ADAPTER_ROOT / "data"


def _manifest() -> dict[str, Any]:
    return json.loads((ADAPTER_ROOT / "manifest.json").read_text(encoding="utf-8"))


def _task(task_id: str) -> dict[str, Any]:
    tasks = _manifest()["tasks"]
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise ValueError(f"unknown DesignBench task {task_id!r}")


def _upstream_root() -> Path:
    configured = os.environ.get("DESIGNBENCH_ROOT")
    candidates = [
        Path(configured).expanduser() if configured else None,
        PROJECT_ROOT.parent / "benchmarks" / "DesignBench",
        ADAPTER_ROOT / "upstream",
    ]
    for candidate in candidates:
        if candidate and (candidate / "web" / "my-react-app" / "package.json").is_file():
            return candidate.resolve()
    raise RuntimeError(
        "DesignBench checkout not found; set DESIGNBENCH_ROOT or clone it into "
        "benchmark/designbench/upstream"
    )


def _initial_and_gold(task: dict[str, Any], metadata: dict[str, Any], task_dir: Path) -> tuple[str, str]:
    kind = task["kind"]
    if kind == "edit":
        return metadata["src_code"], metadata["dst_code"]
    if kind == "repair":
        return metadata["component_jsx"], (task_dir / "repaired.jsx").read_text(encoding="utf-8")
    return metadata["code"], metadata.get("repaired_code") or (task_dir / "repaired.jsx").read_text(encoding="utf-8")


def prepare(
    task_id: str,
    *,
    gold: bool = False,
    force: bool = False,
    condition: str | None = None,
    repetition: int = 1,
) -> Path:
    require_command("git")
    require_command("node")
    require_command("npm")
    manifest = _manifest()
    task = _task(task_id)
    source_id = task["source_id"]
    task_dir = DATA_ROOT / task["kind"] / "react" / str(source_id)
    metadata_path = task_dir / f"{source_id}.json"
    if not metadata_path.is_file():
        raise RuntimeError("DesignBench subset is missing; run python3 scripts/fetch_designbench_subset.py")

    upstream = _upstream_root()
    template = upstream / "web" / "my-react-app"
    dependencies = template / "node_modules"
    if not dependencies.is_dir():
        raise RuntimeError(f"dependencies missing; run npm --prefix {template} ci")

    variant = "gold" if gold else "initial"
    if condition is None:
        target = PROJECT_ROOT / "runs" / "designbench" / task_id / variant
    else:
        if condition not in {"single", "dev-qa"}:
            raise ValueError("condition must be 'single' or 'dev-qa'")
        if gold:
            raise ValueError("gold workspaces cannot be used as agent experiment inputs")
        if repetition < 1:
            raise ValueError("repetition must be positive")
        target = PROJECT_ROOT / "runs" / "designbench" / task_id / condition / f"r{repetition}"
    target = target.resolve()
    runs_root = (PROJECT_ROOT / "runs").resolve()
    if not target.is_relative_to(runs_root):
        raise RuntimeError("refusing to prepare outside runs/")
    if target.exists():
        if not force:
            raise FileExistsError(f"workspace already exists: {target}; pass --force")
        shutil.rmtree(target)

    shutil.copytree(
        template,
        target,
        ignore=shutil.ignore_patterns("node_modules", ".next", ".git"),
    )
    (target / "node_modules").symlink_to(dependencies, target_is_directory=True)
    metadata = json.loads(metadata_path.read_text(encoding="utf-8-sig"))
    initial, reference = _initial_and_gold(task, metadata, task_dir)
    (target / "app" / "page.tsx").write_text(reference if gold else initial, encoding="utf-8")

    prompt = PROJECT_ROOT / "benchmark" / "designbench" / task["prompt_file"]
    shutil.copy2(prompt, target / "TASK.md")
    if manifest["mode"] != "code":
        reference_dir = target / "reference"
        reference_dir.mkdir()
        if task["kind"] == "edit":
            shutil.copy2(task_dir / f"{metadata['src_id']}.png", reference_dir / "input.png")
        elif task["kind"] == "repair":
            shutil.copy2(task_dir / f"{source_id}.png", reference_dir / "input.png")
            shutil.copy2(task_dir / f"{source_id}_mark.png", reference_dir / "marked.png")

    harness_dir = target / ".harness"
    harness_dir.mkdir()
    shutil.copy2(ADAPTER_ROOT / "render-smoke.mjs", harness_dir / "render-smoke.mjs")
    package_path = target / "package.json"
    package = json.loads(package_path.read_text(encoding="utf-8"))
    package.setdefault("scripts", {})["verify:agent"] = "node .harness/render-smoke.mjs"
    package_path.write_text(json.dumps(package, indent=2) + "\n", encoding="utf-8")

    run_manifest = {
        "schema_version": 1,
        "task": task,
        "variant": variant,
        "benchmark_revision": manifest["revision"],
        "dataset_revision": manifest["dataset_revision"],
        "mode": manifest["mode"],
        "target_assets_exposed": False,
    }
    (target / "run-manifest.json").write_text(
        json.dumps(run_manifest, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    for command in (
        ["git", "init", "-q"],
        ["git", "config", "user.name", "DesignBench Adapter"],
        ["git", "config", "user.email", "harness@example.invalid"],
        ["git", "add", "."],
        ["git", "commit", "-q", "-m", f"fixture: {task_id} {variant}"],
    ):
        subprocess.run(command, cwd=target, check=True)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id")
    parser.add_argument("--gold", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--condition", choices=("single", "dev-qa"))
    parser.add_argument("--repetition", type=int, default=1)
    args = parser.parse_args()
    print(
        prepare(
            args.task_id,
            gold=args.gold,
            force=args.force,
            condition=args.condition,
            repetition=args.repetition,
        )
    )


if __name__ == "__main__":
    main()
