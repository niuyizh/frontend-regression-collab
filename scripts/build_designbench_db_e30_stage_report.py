"""Build a visual report from the saved DesignBench db-e30 Dev-QA trajectory."""

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


RUN_ID = "db-e30__dev-qa__r2"
RUN_DIR = PROJECT_ROOT / "runs" / "designbench" / "db-e30" / "dev-qa" / "r2"
RESULT_DIR = PROJECT_ROOT / "results" / "designbench" / "raw" / RUN_ID
OUTPUT_DIR = PROJECT_ROOT / "reports" / "designbench-db-e30-agent-stage-demo"
NODE_BIN = Path("/home/niuyizhuo/.conda/envs/node22/bin")
NODE_MODULES = Path("/nfs-data2/niuyizhuo/benchmarks/DesignBench/web/my-react-app/node_modules")
SOURCE_FILE = "app/page.tsx"


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
    return patch.split("\n\n\n[Budget:", 1)[0].rstrip() + "\n"


def final_patch() -> str:
    return run(["git", "diff", "--binary", "HEAD", "--", SOURCE_FILE], cwd=RUN_DIR)


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
    os.symlink(NODE_MODULES, destination / "node_modules")


def prepare_stage(destination: Path, patch: str | None) -> None:
    destination.mkdir(parents=True)
    extract_initial(destination)
    if patch:
        run(["git", "apply", "--whitespace=nowarn", "-"], cwd=destination, input_text=patch)


def wait_for_server(url: str) -> None:
    deadline = time.monotonic() + 40
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.25)
    raise RuntimeError(f"server did not become ready: {url}")


def screenshot(stage_dir: Path, port: int, target: Path) -> None:
    env = os.environ.copy()
    env["PATH"] = f"{NODE_BIN}:{env['PATH']}"
    server = subprocess.Popen(
        ["npm", "run", "dev", "--", "--hostname", "127.0.0.1", "--port", str(port)],
        cwd=stage_dir,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    try:
        url = f"http://127.0.0.1:{port}/"
        wait_for_server(url)
        subprocess.run(
            [
                "npx", "--no-install", "playwright", "screenshot",
                "--browser", "chromium",
                "--viewport-size", "1792,925",
                "--wait-for-timeout", "900",
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
    before = (developer_dir / SOURCE_FILE).read_text(encoding="utf-8").splitlines(keepends=True)
    after = (final_dir / SOURCE_FILE).read_text(encoding="utf-8").splitlines(keepends=True)
    return "".join(
        difflib.unified_diff(before, after, fromfile=f"a/{SOURCE_FILE}", tofile=f"b/{SOURCE_FILE}")
    )


def write_report(developer_diff: str, repair_diff: str) -> None:
    record = json.loads((RESULT_DIR / "result.json").read_text(encoding="utf-8"))
    workflow = record["workflow_result"]
    evaluation = record["evaluation"]
    report_data = {
        "run_id": RUN_ID,
        "task": record["task"],
        "condition": record["condition"],
        "global_budget": record["budget"],
        "total_tokens": workflow["tokens_spent"],
        "agent_seconds": record["agent_seconds"],
        "developer_outcome": workflow["developer_outcome"],
        "qa_outcome": workflow["qa_outcome"],
        "repair_outcome": workflow["repair_outcome"],
        "qa_verdict": workflow["qa"]["verdict"],
        "external_evaluation": {
            "passed": evaluation["passed"],
            "render_passed": evaluation["render_passed"],
            "structural_passed": evaluation["structural_passed"],
            "visual_progress": evaluation["visual_progress"],
            "hidden_checks": evaluation["visual"]["checks"],
        },
    }
    (OUTPUT_DIR / "report.json").write_text(
        json.dumps(report_data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    (OUTPUT_DIR / "developer.patch").write_text(developer_diff, encoding="utf-8")
    (OUTPUT_DIR / "repair.patch").write_text(repair_diff, encoding="utf-8")

    dev = workflow["developer_outcome"]
    qa = workflow["qa_outcome"]
    repair = workflow["repair_outcome"]
    qa_report = workflow["qa"]["report"]
    document = f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>DesignBench db-e30 Agent 轨迹</title>
  <style>
    :root {{ color-scheme:light; --ink:#17211e; --muted:#64716d; --line:#d9e1de; --paper:#f4f7f6; --green:#137052; --red:#a33b32; --blue:#315f88; --amber:#94630c; }}
    * {{ box-sizing:border-box; }}
    body {{ margin:0; font:15px/1.6 Inter,ui-sans-serif,system-ui,sans-serif; color:var(--ink); background:var(--paper); }}
    header {{ padding:52px max(24px,calc((100vw - 1200px)/2)); color:white; background:linear-gradient(125deg,#123b31,#285d50); }}
    header h1 {{ margin:0 0 10px; font-size:34px; }} header p {{ max-width:900px; margin:0; color:#d8ebe5; }}
    main {{ width:min(1200px,calc(100% - 36px)); margin:28px auto 72px; }}
    .facts {{ display:grid; grid-template-columns:repeat(5,1fr); gap:12px; }}
    .fact,.stage,.flow {{ background:white; border:1px solid var(--line); border-radius:15px; box-shadow:0 8px 28px rgba(20,48,41,.06); }}
    .fact {{ padding:16px 18px; }} .fact strong {{ display:block; font-size:21px; }} .fact span {{ color:var(--muted); font-size:13px; }}
    .flow {{ margin:24px 0; padding:22px; }} .flow h2 {{ margin:0 0 16px; font-size:18px; }}
    .flowline {{ display:grid; grid-template-columns:1fr auto 1fr auto 1fr; align-items:center; gap:10px; }}
    .node {{ min-height:102px; padding:14px; border:1px solid var(--line); border-radius:12px; }} .node b {{ display:block; color:var(--blue); }}
    .node.fail b {{ color:var(--red); }} .node.pass b {{ color:var(--green); }} .arrow {{ color:#80908b; font-size:25px; }}
    .stage {{ margin-top:20px; overflow:hidden; }}
    .stage-head {{ display:flex; justify-content:space-between; gap:16px; padding:18px 22px; border-bottom:1px solid var(--line); }}
    .stage-head h2 {{ margin:0; font-size:20px; }} .badge {{ white-space:nowrap; align-self:center; padding:4px 10px; border-radius:999px; color:var(--green); background:#e6f3ee; font-weight:700; }}
    .badge.fail {{ color:var(--red); background:#f9e9e7; }} .badge.base {{ color:var(--blue); background:#eaf0f6; }}
    .stage-body {{ display:grid; grid-template-columns:minmax(0,1.45fr) minmax(310px,.55fr); }}
    .visual {{ padding:18px; background:#edf2f0; }} .visual img {{ display:block; width:100%; border:1px solid #cbd5d1; border-radius:9px; }}
    .zoom {{ height:190px; margin-bottom:12px; overflow:hidden; border:1px solid #cbd5d1; border-radius:9px; background:#fff; }}
    .zoom img {{ width:178%; max-width:none; transform:translateX(-43.8%); transform-origin:top left; border:0; border-radius:0; }}
    .notes {{ padding:20px 22px; }} .notes h3 {{ margin:0 0 8px; }} .notes ul {{ padding-left:20px; }}
    code {{ padding:2px 5px; border-radius:4px; background:#edf1ef; }}
    details {{ border-top:1px solid var(--line); }} summary {{ cursor:pointer; padding:14px 22px; font-weight:700; }}
    pre {{ overflow:auto; max-height:420px; margin:0; padding:18px; color:#e8f1ed; background:#13211d; font:12px/1.55 ui-monospace,monospace; }}
    .qa {{ white-space:pre-wrap; padding-left:14px; border-left:4px solid var(--red); color:#3d4945; }}
    .readonly {{ padding:14px 22px; border-bottom:1px solid #eadcb7; background:#fff8e8; }} footer {{ margin-top:25px; color:var(--muted); }}
    @media(max-width:850px) {{ .facts {{ grid-template-columns:1fr 1fr; }} .flowline {{ grid-template-columns:1fr; }} .arrow {{ transform:rotate(90deg); text-align:center; }} .stage-body {{ grid-template-columns:1fr; }} }}
  </style>
</head>
<body>
<header>
  <h1>DesignBench db-e30 · 每个 Agent 做了什么</h1>
  <p>真实运行 <strong>{RUN_ID}</strong>。轨迹由 Git 初始提交、QA 实际收到的 Developer diff、OpenCollab session 与最终工作区重建，并非事后虚构示例。</p>
</header>
<main>
  <section class="facts">
    <div class="fact"><strong>48,000</strong><span>相同实验全局预算</span></div>
    <div class="fact"><strong>{workflow['tokens_spent']:,}</strong><span>实际总 token</span></div>
    <div class="fact"><strong>{record['agent_seconds']:.2f}s</strong><span>Agent wall time</span></div>
    <div class="fact"><strong>3</strong><span>Agent 调用 / 角色阶段</span></div>
    <div class="fact"><strong>PASS</strong><span>最终外部评分</span></div>
  </section>

  <section class="flow">
    <h2>协作轨迹图</h2>
    <div class="flowline">
      <div class="node"><b>① Frontend Developer</b>实现无边框、连续按钮；同时把外层 <code>p-4</code> 改成 <code>p-2</code>。</div>
      <div class="arrow">→</div>
      <div class="node fail"><b>② Regression QA · FAIL</b>只审 diff，不重复 smoke test；发现外层 padding 是非需求改动。</div>
      <div class="arrow">→</div>
      <div class="node pass"><b>③ Repair Developer</b>只恢复 <code>p-4</code>，保留所有需求改动；重新验证后通过。</div>
    </div>
  </section>

  <article class="stage">
    <div class="stage-head"><h2>Stage 0 · DesignBench 初始页面</h2><span class="badge base">基线</span></div>
    <div class="stage-body"><div class="visual"><div class="zoom"><img src="initial.png" alt="初始工具栏局部"></div><img src="initial.png" alt="初始 DesignBench 页面"></div><div class="notes"><h3>修改前</h3><ul><li>工具栏本来已经 <code>sticky top-0</code>。</li><li>按钮是 <code>outline</code>，组之间有边框和较大空隙。</li><li>外层 padding 为 <code>p-4</code>。</li></ul></div></div>
  </article>

  <article class="stage">
    <div class="stage-head"><h2>Stage 1 · Frontend Developer</h2><span class="badge">completed · {dev['tokens']:,} tokens · {dev['steps']} steps</span></div>
    <div class="stage-body"><div class="visual"><div class="zoom"><img src="developer.png" alt="Developer 工具栏局部"></div><img src="developer.png" alt="Developer 修改后的页面"></div><div class="notes"><h3>完成了需求主体，也越界改了一处</h3><ul><li>5 个按钮 <code>outline → ghost</code>，去掉边框。</li><li>移除组间 <code>space-x-4</code>、分隔边框和 padding，四个主按钮连续排列。</li><li>保留 Mail、Trash、Reply、Forward、Search。</li><li><strong>非需求改动：</strong>外层 <code>p-4 → p-2</code>，改变整条工具栏高度和边缘留白。</li><li>运行 render smoke，HTTP 200。</li></ul></div></div>
    <details><summary>查看 Developer 交给 QA 的真实 diff</summary><pre>{html.escape(developer_diff)}</pre></details>
  </article>

  <article class="stage">
    <div class="stage-head"><h2>Stage 2 · Regression QA</h2><span class="badge fail">FAIL · {qa['tokens']:,} tokens · {qa['steps']} step</span></div>
    <div class="readonly"><strong>QA 后为什么没有另一张新页面？</strong> 这个 Agent 被刻意设计成只读 diff reviewer；它不能改代码，产物是诊断与有界修复建议。</div>
    <div class="stage-body"><div class="visual"><div class="zoom"><img src="developer.png" alt="QA 检查的 Developer 页面"></div><img src="developer.png" alt="QA 阶段页面保持不变"></div><div class="notes"><h3>QA 的实际工作</h3><div class="qa">{html.escape(qa_report)}</div></div></div>
  </article>

  <article class="stage">
    <div class="stage-head"><h2>Stage 3 · Repair Developer</h2><span class="badge">completed · {repair['tokens']:,} tokens · {repair['steps']} steps</span></div>
    <div class="stage-body"><div class="visual"><div class="zoom"><img src="final.png" alt="Repair 后工具栏局部"></div><img src="final.png" alt="最终 DesignBench 页面"></div><div class="notes"><h3>只修 QA 指出的回归</h3><ul><li>把外层 toolbar padding 恢复为 <code>p-4</code>。</li><li>保留 ghost、无分隔、连续排列和 sticky。</li><li>再次运行 render smoke 并通过。</li><li>外部评分：render、结构检查全部通过；visual progress <strong>{evaluation['visual_progress']:.3f}</strong>。</li><li>5 项隐藏检查全部为 true。</li></ul></div></div>
    <details><summary>查看 Repair 相对 Stage 1 的唯一修改</summary><pre>{html.escape(repair_diff)}</pre></details>
  </article>
  <footer>Provenance: <code>results/designbench/raw/{RUN_ID}/</code> · Rebuild: <code>python scripts/build_designbench_db_e30_stage_report.py</code></footer>
</main>
</body>
</html>
"""
    (OUTPUT_DIR / "index.html").write_text(document, encoding="utf-8")


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    dev_patch = developer_patch()
    with tempfile.TemporaryDirectory(prefix="db-e30-stage-demo-") as temp:
        root = Path(temp)
        initial_dir = root / "initial"
        developer_dir = root / "developer"
        final_dir = root / "final"
        prepare_stage(initial_dir, None)
        prepare_stage(developer_dir, dev_patch)
        prepare_stage(final_dir, final_patch())
        fix_patch = repair_patch(developer_dir, final_dir)
        screenshot(initial_dir, 4321, OUTPUT_DIR / "initial.png")
        screenshot(developer_dir, 4322, OUTPUT_DIR / "developer.png")
        screenshot(final_dir, 4323, OUTPUT_DIR / "final.png")
        write_report(dev_patch, fix_patch)
    print(f"wrote {OUTPUT_DIR / 'index.html'}")


if __name__ == "__main__":
    main()
