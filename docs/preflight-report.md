# 开跑前检查报告

初次检查：2026-11-20；最近复核：2026-11-22（Asia/Shanghai）

## 环境

- OpenCollab：0.9.6，`78ca8e374181f621e70e8d5436199182f8295cbf`
- OpenCollab `.venv`：Python 3.13.9，`uv sync --locked --extra dev` 无待变更包
- Node.js：22.23.2
- npm：10.9.8
- Playwright Test：1.65.1
- Chromium：已安装且公开测试实际启动成功
- DeepSeek：`https://api.deepseek.com` 鉴权成功，模型列表包含 `deepseek-flash`

开跑前的 API 鉴权只使用模型列表接口，没有发送生成任务；正式运行已于
2026-11-22 完成，结果另见 `experiment-results.md`。

## 工程验证

| 检查 | 结果 |
|---|---|
| 固定应用 TypeScript + Vite build | 通过 |
| 公开回归测试 | 6/6 通过 |
| Python harness 单测 | 24/24 通过 |
| OpenCollab workflow discovery | 三个项目 workflow 均发现 |
| dry-run matrix | 18 次，未调用模型 |
| 未实现 T01 的隐藏评分 smoke | build/public 通过，hidden 0/2，符合预期 |
| T01 oracle | build/public/hidden 通过，2/2 |
| T02 oracle | build/public/hidden 通过，2/2 |
| T03 oracle | build/public/hidden 通过，2/2 |
| T04 oracle | build/public/hidden 通过，2/2 |
| T05 oracle | build/public/hidden 通过，2/2 |

Oracle 只验证任务可解和测试正确，临时解与结果已清理，不作为 Agent 实验数据。

## 已完成的后续工作

1. 16k Single 与 24k Developer 子上限均被真实 smoke 否决；当前两组共享相同 48k 全局上限，并取消不必要的结构化纠正与重复 QA 探索。
2. 48k 修订预算的 Single 与 Dev-QA smoke 均通过外部评分；校准证据不进入正式结果。
3. 从真实日志和源码中定位到结构化子 Agent 预算停止状态不向父工作流显式传播的可观测性问题。
4. 已检索 OpenCollab 已有 issue，完成离线最小复现、脱敏日志、issue 草稿和项目侧状态传播改进。
5. 改进已加入回归测试；完整 harness 24/24 通过，Ruff 通过。
6. 正式 18-run 矩阵、9 次 artifact-first 改进矩阵及 DesignBench 三次配对已完成。

## 尚未完成

1. 在 GitHub 创建项目远端并提交 issue；当前机器尚无可用的 GitHub API 登录。
2. 将本地已完成的结果文档发布到 GitHub，并回填两个公开链接。
