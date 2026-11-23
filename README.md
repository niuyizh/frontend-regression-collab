# Frontend Regression Collaboration

一个基于 OpenCollab 的可复现多智能体项目，用于检验：在固定总 token 预算下，将第二个智能体专门用于前端回归检查，是否比单个 Frontend Developer 更能保留旧功能和未显式覆盖的 UI 状态。

当前仓库已经包含固定前端应用、5 个任务、单智能体基线、严格与
artifact-first 两种 Developer→Regression QA→Developer 工作流、公开/隐藏测试、
批量运行器、27 次正式运行以及 DesignBench 三次配对。原始轨迹、失败案例和统计均已
提交；实验结论见 [docs/experiment-results.md](docs/experiment-results.md)。

一组真实的逐 Agent 可视化轨迹见
[T03 Developer→QA→Repair HTML 报告](reports/t03-agent-stage-demo/index.html)；
[GitHub 可直接查看的整页预览](reports/t03-agent-stage-demo/README.md)同时展示初始、
Developer、只读 QA 和 Repair 四个阶段。

DesignBench 的真实 Agent 分工可查看
[db-e30 协作轨迹 HTML](reports/designbench-db-e30-agent-stage-demo/index.html)；
[GitHub 整页预览](reports/designbench-db-e30-agent-stage-demo/README.md)展示 Developer
实现、Regression QA 定位非需求回归，以及 Repair Developer 有界修复的全过程。

公开交付链接：

- 项目仓库：https://github.com/niuyizh/frontend-regression-collab
- OpenCollab issue：暂时撤回，待补充验证后重新公开

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

Artifact-first Dev-QA（改进）
同样的角色、提示、模型与预算，但 coding role 停止且留下干净非空 diff 时，
允许以 diff 继续交接；空 diff 或外部验收失败仍判失败。
```

两个条件使用相同模型、任务、初始仓库、48k 全局预算上限和外部评分器。Dev-QA 的角色上限之和可以超过 48k，但它们顺序共享同一个全局池，后续角色只能使用前序实际未消耗的额度。Developer 和 Repair 使用状态可见的自由文本 `agent_run()`；QA 只接收任务、Developer 报告和完整 diff，用一次无工具调用返回可解析 verdict，避免重复公开测试和仓库探索。QA 不具有写文件工具；它必须检查 Developer 没有覆盖的旧行为并给出 diff 证据，不能为了体现角色价值而虚构问题。

## 为什么需要多智能体

单 Agent 可以自检，但“实现新需求”和“主动寻找自己实现遗漏的回归”共享同一上下文、计划和注意力。这里的多智能体设计不是简单增加一次泛化 review，而是引入三个可检验的机制：

1. 独立角色提示将 QA 注意力限定在旧功能和遗漏状态。
2. QA 为只读角色，不能用重写实现来掩盖诊断质量。
3. QA 单次上限为 6k token，且仅在 FAIL 时触发一次上限 18k 的修复；三阶段顺序共享 48k 全局池，控制协作开销。

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

除自建固定应用外，仓库还接入了一个无需 Docker 的 DesignBench React
适配/校准子集。五题清单与固定上游 revision 位于
`benchmark/designbench/manifest.json`，逐题说明位于
`benchmark/designbench/prompts/`。下载后的题目资源保存在
`benchmark/designbench/data/`，上游 checkout 当前位于相邻目录
`../benchmarks/DesignBench`；两者都不提交 Git。适配器的完整说明见
[`benchmark/designbench/README.md`](benchmark/designbench/README.md)。

## 环境

本次确认的环境：

- OpenCollab 0.9.6，Git revision `78ca8e374181f621e70e8d5436199182f8295cbf`
- Python 3.13.9，OpenCollab 使用其独立 `.venv`
- Node.js 22.23.2，npm 10.9.8（Conda 环境 `node22`）
- Playwright Test 1.65.1，仅安装 Chromium
- React 19.3.1、Vite 8.3.8、TypeScript 7.0.2
- DeepSeek V4.1 Flash，API ID `deepseek-flash`，Responses protocol，reasoning effort `low`

`deepseek-flash` 是服务端别名而非不可变权重哈希。正式矩阵已在同一时间窗口连续
运行并保留每次响应和轨迹；无法获得供应商权重哈希仍是已知限制。

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

预注册的 18 次原始矩阵与 9 次 artifact-first 改进矩阵：

```bash
python scripts/run_matrix.py --execute
python scripts/run_resilient_matrix.py --execute
python scripts/summarize_results.py
```

每次运行从 `benchmark/base-app` 复制干净仓库，提交初始 Git 快照，保存 OpenCollab transcript/trace、模型输出、代码差异、构建日志、公开测试和隐藏评分。`results/runs.csv` 与 `results/summary.json` 只从真实原始结果生成。

### DesignBench 五题适配校准与单题 Agent 实验

这里必须区分两个范围：五道题都完成了数据下载、initial/gold 可解性与评分器校准；
只有 `db-e30` 运行了付费 Agent，并按 Single/Dev-QA 各三次进入比较统计。其余四题
不属于 Agent 效果数据，它们只验证适配器覆盖不同 Edit/Compile 类型。若要声称
“DesignBench 五题上的 Agent 结果”，还必须正式运行那四题。

首次下载选定题目并准备依赖：

```bash
conda activate node22
python3 scripts/fetch_designbench_subset.py
npm --prefix ../benchmarks/DesignBench/web/my-react-app ci
```

生成一个不含 gold 答案和参考截图的 code-mode 工作区，并做页面渲染 smoke：

```bash
python3 scripts/prepare_designbench.py db-e11 --condition dev-qa --repetition 1 --force
npm --prefix runs/designbench/db-e11/dev-qa/r1 run verify:agent
```

使用工作区外的隐藏结构检查和视觉指标评分：

```bash
python3 scripts/score_designbench.py \
  db-e11 runs/designbench/db-e11/dev-qa/r1 \
  --output-dir results/designbench/manual/db-e11
```

下面的命令默认只打印 OpenCollab 运行计划，不调用模型 API；只有显式加入
`--execute --force` 才会产生付费调用：

```bash
python3 scripts/run_designbench_experiment.py db-e11 dev-qa --repetition 1
```

外部适配器现在记录渲染结果、隐藏 DOM 结构检查、固定视口截图、像素相似度和
归一化 MAE 相似度。Edit 题只有在全部结构检查通过，且相对于 frozen
initial→gold 的 MAE 视觉进展至少达到 50% 时才算完成；Compile 题以页面修复后
能否渲染为准。DesignBench gold 是静态截图参考，不是交互功能真值，因此该子集
只作为静态编辑/编译的外部辅助验证；项目自建隐藏 Playwright 任务仍承担正式的
功能完成率与回归结论。

`db-e30` 的首轮付费 pilot 暴露了全文读取导致的角色预算耗尽，以及评分器对
特定 DOM 包装方式过拟合的问题。保留 r1 失败后，在不增加预算的情况下改为
范围读取并修正几何评分。相同修订协议下的 r2 配对中，Single 使用 14,333
token、25.962 秒，因加入未要求的视觉改动而失败；Dev-QA 使用 24,532 token、
50.830 秒，QA 从 diff 发现 Developer 擅自缩小 toolbar 外边距，Repair 修复后
通过（视觉进度 0.798）。相同协议的 r2-r4 三次配对中，Single 通过 2/3，Dev-QA
通过 3/3；Dev-QA 平均多用 6,156 token、慢 11.23 秒。详细证据和限制见
[docs/designbench-validation.md](docs/designbench-validation.md) 与
[results/designbench/README.md](results/designbench/README.md)。

## 任务与指标

5 个任务覆盖搜索/空状态、模态框键盘与取消路径、异步失败恢复、响应式导航、表单校验与持久化。详细协议见 [docs/experiment-protocol.md](docs/experiment-protocol.md)。

主要指标：任务完成率、公开回归通过率、隐藏需求通过数、Agent 耗时和 token 消耗。任务完成要求构建、全部公开测试、全部任务隐藏测试通过，且不得修改测试或 `package.json`。

## 正式结果摘要

| 条件 | 严格完成率 | 平均 token | 平均 Agent 秒 |
|---|---:|---:|---:|
| Single | 8/9（88.9%） | 35,690 | 26.29 |
| 原始 Dev-QA | 2/9（22.2%） | 26,472 | 23.26 |
| artifact-first Dev-QA | 7/9（77.8%） | 29,235 | 32.06 |

原始方案因“已有有效 diff、但最终文字报告未生成”而频繁阻断 QA。artifact-first
改进恢复了 7 次 Developer 交接和 2 次 Repair 交接，使完成率增加 55.6 个百分点，
但仍未超过 Single；两次剩余失败来自 QA 输出截断。QA 在 T01 与 T03 找到两个有
diff 证据的旧状态回归并触发修复。完整波动、成本与局限见结果文档。

## 当前状态

- 固定应用构建通过。
- 6 个公开回归测试通过。
- 5 个任务均经过临时 oracle 可解性验证：各自构建、公开测试和 2/2 隐藏测试通过。
- 24 项 harness 单测与 Ruff 检查通过，OpenCollab 能发现三个自定义工作流。
- API 鉴权和模型可见性已验证。
- 首次 16k 真实预算校准在实现前停止；失败轨迹已保留于本地，分析见 [docs/failure-cases.md](docs/failure-cases.md)。
- 48k 最终 smoke：Single 使用 28,218 token、23.6 秒，Dev-QA 使用 29,335 token、37.4 秒；两者构建、6/6 公开测试和 2/2 隐藏测试均通过。该校准任务只证明协议可运行，不计入正式比较。
- 正式 18-run 原始矩阵和 9-run 改进矩阵已经完成并保留全部原始结果。
- DesignBench code-mode 五题已下载并完成适配器校准；四个 Edit 题均完成 initial-fail、
  gold-pass 的结构与视觉校准，Compile 题的 initial 按预期返回 HTTP 500、gold
  返回 HTTP 200。当前 DeepSeek 账户只暴露 `deepseek-flash` 和
  `deepseek-v4-pro`，没有视觉模型，因此没有纳入依赖图像输入的 Repair 题。
  只有 `db-e30` 进行了正式 Agent 比较，三次固定配对结果为 Single 2/3、Dev-QA
  3/3；其他四题不能计作 Agent 实验结果。
- 框架问题的离线最小复现、项目侧状态传播改进和相同条件验证已经完成；
  原公开 issue 已暂时撤回，待补充验证后重新提交。

开跑前记录见 [docs/preflight-report.md](docs/preflight-report.md)，研究依据与
OpenCollab benchmark 适配分析见
[docs/research-basis-and-benchmark-fit.md](docs/research-basis-and-benchmark-fit.md)。
