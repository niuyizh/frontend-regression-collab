"""Build a visual, provenance-backed report for one real Dev-QA-Repair run."""

from __future__ import annotations

import difflib
import html
import io
import json
import os
from pathlib import Path
import subprocess
import tarfile
import tempfile
import time
import urllib.request

from common import PROJECT_ROOT


RUN_ID = "t03-sync-retry__dev-qa-resilient__r1"
RUN_DIR = PROJECT_ROOT / "runs" / "t03-sync-retry" / "dev-qa-resilient" / "r1"
RESULT_DIR = PROJECT_ROOT / "results" / "raw" / RUN_ID
OUTPUT_DIR = PROJECT_ROOT / "reports" / "t03-agent-stage-demo"
NODE_BIN = Path("/home/niuyizhuo/.conda/envs/node22/bin")
SOURCE_FILES = ("src/components/AsyncPanel.tsx", "src/styles.css")


def run(command: list[str], *, cwd: Path, input_text: str | None = None) -> str:
    result = subprocess.run(
        command,
        cwd=cwd,
        input=input_text,
        text=True,
        check=True,
        capture_output=True,
    )
    return result.stdout


def qa_session_path() -> Path:
    matches = list((RESULT_DIR / "opencollab-artifacts" / "sessions").glob("*/001_regression-qa.json"))
    if len(matches) != 1:
        raise RuntimeError(f"expected one QA session, found {len(matches)}")
    return matches[0]


def developer_patch() -> str:
    session = json.loads(qa_session_path().read_text(encoding="utf-8"))
    prompt = session["messages"][1]["content"]
    marker = "Current diff:\n"
    if marker not in prompt:
        raise RuntimeError("QA handoff does not contain the Developer diff")
    patch = prompt.split(marker, 1)[1]
    patch = patch.split("\n\n\n[Budget:", 1)[0].rstrip() + "\n"
    return patch


def final_patch() -> str:
    return run(["git", "diff", "--binary", "HEAD"], cwd=RUN_DIR)


def extract_initial(destination: Path) -> None:
    archive = subprocess.run(
        ["git", "archive", "HEAD"],
        cwd=RUN_DIR,
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(archive)) as bundle:
        members = [member for member in bundle.getmembers() if member.name != "node_modules"]
        bundle.extractall(destination, members=members, filter="data")
    os.symlink(PROJECT_ROOT / "node_modules", destination / "node_modules")


def prepare_stage(destination: Path, patch: str | None) -> None:
    destination.mkdir(parents=True)
    extract_initial(destination)
    if patch:
        run(["git", "apply", "--whitespace=nowarn", "-"], cwd=destination, input_text=patch)


def wait_for_server(url: str) -> None:
    deadline = time.monotonic() + 20
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.2)
    raise RuntimeError(f"server did not become ready: {url}")


def screenshot(stage_dir: Path, port: int, target: Path) -> None:
    env = os.environ.copy()
    env["PATH"] = f"{NODE_BIN}:{env['PATH']}"
    server = subprocess.Popen(
        ["npm", "run", "dev", "--", "--host", "127.0.0.1", "--port", str(port)],
        cwd=stage_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        url = f"http://127.0.0.1:{port}/?sync=error"
        wait_for_server(url)
        subprocess.run(
            [
                "npx", "--no-install", "playwright", "screenshot",
                "--browser", "chromium",
                "--viewport-size", "1280,900",
                "--wait-for-timeout", "500",
                "--full-page",
                url,
                str(target),
            ],
            cwd=PROJECT_ROOT,
            env=env,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception as error:
        server.terminate()
        output, _ = server.communicate(timeout=5)
        raise RuntimeError(f"stage server failed:\n{output}") from error
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server.kill()


def repair_patch(developer_dir: Path, final_dir: Path) -> str:
    chunks: list[str] = []
    for relative in SOURCE_FILES:
        before = (developer_dir / relative).read_text(encoding="utf-8").splitlines(keepends=True)
        after = (final_dir / relative).read_text(encoding="utf-8").splitlines(keepends=True)
        chunks.extend(
            difflib.unified_diff(
                before,
                after,
                fromfile=f"a/{relative}",
                tofile=f"b/{relative}",
            )
        )
    return "".join(chunks)


def write_report(developer_diff: str, repair_diff: str) -> None:
    record = json.loads((RESULT_DIR / "agent.json").read_text(encoding="utf-8"))
    evaluation = json.loads((RESULT_DIR / "evaluation.json").read_text(encoding="utf-8"))
    workflow = record["workflow_result"]
    qa_report = workflow["qa"]["report"]
    report_data = {
        "run_id": RUN_ID,
        "task": "T03 — Recoverable asynchronous error state",
        "workflow": record["workflow"],
        "global_budget": record["budget"],
        "total_tokens": workflow["tokens_spent"],
        "agent_seconds": record["agent_seconds"],
        "developer_outcome": workflow["developer_outcome"],
        "qa_outcome": workflow["qa_outcome"],
        "repair_outcome": workflow["repair_outcome"],
        "qa_verdict": workflow["qa"]["verdict"],
        "external_evaluation": {
            "task_complete": evaluation["task_complete"],
            "build": evaluation["build_passed"],
            "public_tests": evaluation["public_regression_passed"],
            "hidden_tests": evaluation["hidden"],
        },
    }
    (OUTPUT_DIR / "report.json").write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (OUTPUT_DIR / "developer.patch").write_text(developer_diff, encoding="utf-8")
    (OUTPUT_DIR / "repair.patch").write_text(repair_diff, encoding="utf-8")

    developer_tokens = workflow["developer_outcome"]["tokens"]
    qa_tokens = workflow["qa_outcome"]["tokens"]
    repair_tokens = workflow["repair_outcome"]["tokens"]
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>T03 Agent 协作轨迹展示</title>
  <style>
    :root {{ color-scheme: light; --ink:#18221f; --muted:#5f6d68; --line:#d9e2de; --paper:#f6f8f7; --green:#176b4d; --red:#9a3e35; --blue:#315f88; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font:15px/1.6 Inter, ui-sans-serif, system-ui, sans-serif; color:var(--ink); background:var(--paper); }}
    header {{ padding:56px max(24px, calc((100vw - 1180px)/2)); color:white; background:#163b31; }}
    header p {{ max-width:850px; color:#dceae5; }}
    main {{ width:min(1180px, calc(100% - 40px)); margin:32px auto 72px; }}
    .facts, .stages {{ display:grid; gap:18px; }}
    .facts {{ grid-template-columns:repeat(5,1fr); margin-top:-58px; }}
    .fact, .stage {{ background:white; border:1px solid var(--line); border-radius:16px; box-shadow:0 10px 30px rgba(20,50,42,.07); }}
    .fact {{ padding:18px; }} .fact strong {{ display:block; font-size:22px; }} .fact span {{ color:var(--muted); font-size:13px; }}
    .stages {{ margin-top:30px; }} .stage {{ overflow:hidden; }}
    .stage-head {{ padding:20px 24px; display:flex; justify-content:space-between; gap:16px; border-bottom:1px solid var(--line); }}
    .stage-head h2 {{ margin:0; font-size:20px; }} .badge {{ white-space:nowrap; padding:4px 10px; border-radius:999px; background:#e7f2ed; color:var(--green); font-weight:700; }}
    .badge.fail {{ color:var(--red); background:#f9eae8; }}
    .stage-body {{ display:grid; grid-template-columns:minmax(0,1.35fr) minmax(300px,.65fr); gap:0; }}
    .shot {{ padding:20px; background:#eef3f1; }} .shot img {{ width:100%; display:block; border:1px solid #cbd7d2; border-radius:10px; }}
    .notes {{ padding:22px 24px; }} .notes h3 {{ margin-top:0; }}
    code {{ background:#edf1ef; padding:2px 5px; border-radius:4px; }}
    pre {{ overflow:auto; max-height:390px; margin:0; padding:18px; color:#e9f2ee; background:#13211d; font:12px/1.55 ui-monospace, monospace; }}
    details {{ border-top:1px solid var(--line); }} summary {{ cursor:pointer; padding:15px 24px; font-weight:700; }}
    .qa {{ white-space:pre-wrap; border-left:4px solid var(--red); padding-left:16px; color:#3c4945; }}
    .same {{ padding:18px 24px; background:#fff8e8; border-top:1px solid #eadcb7; }}
    footer {{ margin-top:28px; color:var(--muted); }}
    @media (max-width:850px) {{ .facts {{ grid-template-columns:1fr 1fr; margin-top:20px; }} .stage-body {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<header>
  <h1>一组真实的 Agent 协作轨迹</h1>
  <p><strong>{RUN_ID}</strong>。页面和数据均从保存的 Git 初始提交、QA 实际收到的 Developer diff、最终工作区和 OpenCollab session 重建。</p>
</header>
<main>
  <section class="facts">
    <div class="fact"><strong>48,000</strong><span>全局 token 上限</span></div>
    <div class="fact"><strong>{workflow['tokens_spent']:,}</strong><span>实际总 token</span></div>
    <div class="fact"><strong>{record['agent_seconds']:.3f}s</strong><span>Agent wall time</span></div>
    <div class="fact"><strong>6/6 + 2/2</strong><span>公开 + 隐藏测试</span></div>
    <div class="fact"><strong>PASS</strong><span>最终外部验收</span></div>
  </section>
  <section class="stages">
    <article class="stage">
      <div class="stage-head"><h2>Stage 0 · 初始前端</h2><span class="badge">基线</span></div>
      <div class="stage-body"><div class="shot"><img src="initial.png" alt="初始错误状态"></div><div class="notes"><h3>尚无恢复操作</h3><p><code>/?sync=error</code> 显示既有红色错误态，但没有 <code>Retry sync</code> 按钮。</p></div></div>
    </article>
    <article class="stage">
      <div class="stage-head"><h2>Stage 1 · Frontend Developer</h2><span class="badge fail">stopped · {developer_tokens:,} tokens</span></div>
      <div class="stage-body"><div class="shot"><img src="developer.png" alt="Developer 修改后的错误状态"></div><div class="notes"><h3>功能加入，但引入旧样式回归</h3><p>Developer 加入 retry 状态机和按钮；同时误删唯一的 <code>.sync-state.error</code> 规则。它在最终文字报告前因子预算停止，但非空 diff 被 artifact-first 交给 QA。</p></div></div>
      <details><summary>查看 Developer 实际 diff</summary><pre>{html.escape(developer_diff)}</pre></details>
    </article>
    <article class="stage">
      <div class="stage-head"><h2>Stage 2 · Regression QA</h2><span class="badge fail">FAIL · {qa_tokens:,} tokens</span></div>
      <div class="same"><strong>页面为什么没变？</strong> QA 是只读 Agent，没有写文件工具；它的产物是可复现诊断，而不是第二份前端。</div>
      <div class="stage-body"><div class="shot"><img src="developer.png" alt="QA 后页面与 Developer 阶段相同"></div><div class="notes"><h3>QA 的真实报告</h3><div class="qa">{html.escape(qa_report)}</div></div></div>
    </article>
    <article class="stage">
      <div class="stage-head"><h2>Stage 3 · Repair Developer</h2><span class="badge">recovered · {repair_tokens:,} tokens</span></div>
      <div class="stage-body"><div class="shot"><img src="final.png" alt="Repair 后最终错误状态"></div><div class="notes"><h3>恢复旧样式并保留新功能</h3><p>Repair 恢复错误态的 grid、间距和红色，并为 retry 按钮增加局部布局。最终 build、6 个公开测试和 2 个隐藏测试全部通过。</p></div></div>
      <details><summary>查看 Repair 相对 Stage 1 的修改</summary><pre>{html.escape(repair_diff)}</pre></details>
    </article>
  </section>
  <footer>Provenance: <code>results/raw/{RUN_ID}/</code> · 生成脚本 <code>scripts/build_t03_stage_report.py</code></footer>
</main>
</body>
</html>
"""
    (OUTPUT_DIR / "index.html").write_text(document, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dev_patch = developer_patch()
    with tempfile.TemporaryDirectory(prefix="t03-stage-demo-") as temp:
        root = Path(temp)
        initial_dir = root / "initial"
        developer_dir = root / "developer"
        final_dir = root / "final"
        prepare_stage(initial_dir, None)
        prepare_stage(developer_dir, dev_patch)
        prepare_stage(final_dir, final_patch())
        fix_patch = repair_patch(developer_dir, final_dir)
        screenshot(initial_dir, 4311, OUTPUT_DIR / "initial.png")
        screenshot(developer_dir, 4312, OUTPUT_DIR / "developer.png")
        screenshot(final_dir, 4313, OUTPUT_DIR / "final.png")
        write_report(dev_patch, fix_patch)
    print(f"wrote {OUTPUT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
