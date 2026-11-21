# Frontend Regression Collaboration

一个基于 OpenCollab 的可复现多智能体项目，用于检验：在固定总 token 预算下，将第二个智能体专门用于前端回归检查，是否比单个 Frontend Developer 更能保留旧功能和未显式覆盖的 UI 状态。

当前仓库已经包含固定前端应用、5 个任务、单智能体基线、Developer→Regression QA→Developer 修复工作流、公开/隐藏测试、批量运行器和结果汇总器。正式模型实验尚未执行，因此仓库没有预填任何效果数字。

## 研究问题

Frontend Developer 往往优先完成当前需求和可见测试，而修改周围的旧交互、键盘路径、响应式边界、异步失败态和本地持久化容易遗漏。本项目比较两个条件：

```text
Single（修订校准方案）
任务 → Frontend Developer（全局上限 48k token）→ 评分

Dev-QA
任务 → Frontend Developer（单次上限 30k）
     → Regression QA（单次上限 6k，单次 diff review）
     → 有证据失败时 Developer 修复（单次上限 18k）
     → 评分
```

两个条件使用相同模型、任务、初始仓库、48k 全局预算上限和外部评分器。Dev-QA 的角色上限之和可以超过 48k，但它们顺序共享同一个全局池，后续角色只能使用前序实际未消耗的额度。Developer 和 Repair 使用状态可见的自由文本 `agent_run()`；QA 只接收任务、Developer 报告和完整 diff，用一次无工具调用返回可解析 verdict，避免重复公开测试和仓库探索。QA 不具有写文件工具；它必须检查 Developer 没有覆盖的旧行为并给出 diff 证据，不能为了体现角色价值而虚构问题。

## 为什么需要多智能体

单 Agent 可以自检，但“实现新需求”和“主动寻找自己实现遗漏的回归”共享同一上下文、计划和注意力。这里的多智能体设计不是简单增加一次泛化 review，而是引入三个可检验的机制：

1. 独立角色提示将 QA 注意力限定在旧功能和遗漏状态。
2. QA 为只读角色，不能用重写实现来掩盖诊断质量。
3. QA 只有 3k token，且仅在 FAIL 时触发一次 3k 修复，控制协作开销。

如果复杂状态任务改善、简单任务持平或变慢，说明收益来自回归检查机制而非“多调用一次模型必然更强”。如果没有改善，则要检查同模型错误相关性、交接信息不足和预算切分损失。

## 仓库结构

```text
benchmark/base-app/   固定 React/TypeScript 应用和公开回归测试
tasks/                5 个任务及机器可读 manifest
workflows/            OpenCollab 单 Agent 与 Dev-QA 工作流
evaluator/            不暴露给任务工作区的隐藏 Playwright 测试
scripts/              重置、运行、评分、矩阵和汇总脚本
tests/                harness 与预算/权限单测
results/raw/          正式运行原始日志、轨迹和评分
reproductions/        后续框架问题的最小复现
docs/                 实验协议和开跑前检查
runs/                 临时任务工作区，不提交 Git
```

## 环境

本次确认的环境：

- OpenCollab 0.9.6，Git revision `78ca8e374181f621e70e8d5436199182f8295cbf`
- Python 3.13.9，OpenCollab 使用其独立 `.venv`
- Node.js 22.23.2，npm 10.9.8（Conda 环境 `node22`）
- Playwright Test 1.65.1，仅安装 Chromium
- React 19.3.1、Vite 8.3.8、TypeScript 7.0.2
- DeepSeek V4.1 Flash，API ID `deepseek-flash`，Responses protocol，reasoning effort `low`

`deepseek-flash` 是服务端别名而非不可变权重哈希。正式矩阵应在同一时间窗口连续运行，并保留 `/models` 元数据和每次响应中的模型标识；这是模型版本固定性的已知限制。

## 安装

OpenCollab 在其独立 checkout 中安装：

```bash
cd /path/to/OpenCollab
uv sync --locked --extra dev
```

前端项目使用 Node 环境：

```bash
conda activate node22
cd /path/to/frontend-regression-collab
npm ci
npx --no-install playwright install chromium
```

API Key 保存在 OpenCollab 已忽略的 `configs/.env` 或进程环境中，不复制到本仓库。

## 本地验证

```bash
conda activate node22
cd /path/to/frontend-regression-collab

npm --prefix benchmark/base-app run build
PLAYWRIGHT_HTML_OPEN=never npm --prefix benchmark/base-app run test:public

/path/to/OpenCollab/.venv/bin/python -m pytest -q tests/test_harness.py
```

列出自定义工作流：

```bash
cd /path/to/OpenCollab
OPENCOLLAB_WORKFLOWS_DIR=/path/to/frontend-regression-collab/workflows \
  uv run opencollab workflow list --workspace /path/to/frontend-regression-collab
```

## 运行实验

默认命令只打印计划，不产生 API 消耗：

```bash
conda activate node22
cd /path/to/frontend-regression-collab
python scripts/run_matrix.py
```

单次付费 smoke 必须显式添加 `--execute`：

```bash
python scripts/run_experiment.py t03-sync-retry single --repetition 1 --execute
python scripts/run_experiment.py t03-sync-retry dev-qa --repetition 1 --execute
```

48k 修订方案的 Single 与 Dev-QA smoke 均已通过。确认付费运行后执行预注册的 18 次矩阵：

```bash
python scripts/run_matrix.py --execute
python scripts/summarize_results.py
```

每次运行从 `benchmark/base-app` 复制干净仓库，提交初始 Git 快照，保存 OpenCollab transcript/trace、模型输出、代码差异、构建日志、公开测试和隐藏评分。`results/runs.csv` 与 `results/summary.json` 只从真实原始结果生成。

## 任务与指标

5 个任务覆盖搜索/空状态、模态框键盘与取消路径、异步失败恢复、响应式导航、表单校验与持久化。详细协议见 [docs/experiment-protocol.md](docs/experiment-protocol.md)。

主要指标：任务完成率、公开回归通过率、隐藏需求通过数、Agent 耗时和 token 消耗。任务完成要求构建、全部公开测试、全部任务隐藏测试通过，且不得修改测试或 `package.json`。

## 当前状态

- 固定应用构建通过。
- 6 个公开回归测试通过。
- 5 个任务均经过临时 oracle 可解性验证：各自构建、公开测试和 2/2 隐藏测试通过。
- harness 单测通过，OpenCollab 能发现两个自定义工作流。
- API 鉴权和模型可见性已验证。
- 首次 16k 真实预算校准在实现前停止；失败轨迹已保留于本地，分析见 [docs/failure-cases.md](docs/failure-cases.md)。
- 48k 最终 smoke：Single 使用 28,218 token、23.6 秒，Dev-QA 使用 29,335 token、37.4 秒；两者构建、6/6 公开测试和 2/2 隐藏测试均通过。该校准任务只证明协议可运行，不计入正式比较。
- 正式 18-run 矩阵已具备执行条件但尚未启动，避免未经确认产生大额 API 消耗。
- 框架 issue 草稿、离线最小复现和项目侧状态传播改进已经完成；GitHub issue 链接和正式实验结论尚未产生。

开跑前记录见 [docs/preflight-report.md](docs/preflight-report.md)。
