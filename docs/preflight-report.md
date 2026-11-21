# 开跑前检查报告

检查日期：2026-11-20（Asia/Shanghai）

## 环境

- OpenCollab：0.9.6，`78ca8e374181f621e70e8d5436199182f8295cbf`
- OpenCollab `.venv`：Python 3.13.9，`uv sync --locked --extra dev` 无待变更包
- Node.js：22.23.2
- npm：10.9.8
- Playwright Test：1.65.1
- Chromium：已安装且公开测试实际启动成功
- DeepSeek：`https://api.deepseek.com` 鉴权成功，模型列表包含 `deepseek-flash`

API 鉴权使用模型列表接口，没有发送生成任务。正式模型调用尚未开始。

## 工程验证

| 检查 | 结果 |
|---|---|
| 固定应用 TypeScript + Vite build | 通过 |
| 公开回归测试 | 6/6 通过 |
| Python harness 单测 | 6/6 通过 |
| OpenCollab workflow discovery | `frontend-single`、`frontend-dev-qa` 均发现 |
| dry-run matrix | 18 次，未调用模型 |
| 未实现 T01 的隐藏评分 smoke | build/public 通过，hidden 0/2，符合预期 |
| T01 oracle | build/public/hidden 通过，2/2 |
| T02 oracle | build/public/hidden 通过，2/2 |
| T03 oracle | build/public/hidden 通过，2/2 |
| T04 oracle | build/public/hidden 通过，2/2 |
| T05 oracle | build/public/hidden 通过，2/2 |

Oracle 只验证任务可解和测试正确，临时解与结果已清理，不作为 Agent 实验数据。

## 未完成事项

1. 16k Single smoke 已运行并在实现前因预算预留停止；已修订为两组共享相同 36k 全局上限，并取消 Developer 不必要的结构化纠正会话。
2. 用 36k 修订预算运行一对真实 API smoke，检查代码落盘和两种条件轨迹。
3. 正式运行 18 次矩阵并汇总。
4. 从真实日志和源码中定位至少一个框架问题或设计局限。
5. 检索已有 issue，准备最小复现和脱敏日志。
6. 实现改进、回归测试和同条件前后对比。
7. 补充 GitHub 仓库、issue 和可能的 PR 链接。
