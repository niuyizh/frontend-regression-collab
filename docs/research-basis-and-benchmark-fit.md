# 研究依据与 benchmark 适配分析

检查日期：2026-11-21（Asia/Shanghai）

## 1. 结论先行

“Frontend Developer 实现新需求，Regression QA 专查旧功能和遗漏 UI
状态”是一个值得实验验证的真实问题，但不能在正式结果出来前声称它一定优于
单 Agent。现有研究支持两点：代码审查适合角色化协作；多 Agent 在部分复杂编码
任务上能提高完成率。它们也同时说明，多 Agent 会显著增加 token，而且在一些
任务上的改善并不稳定。因此，本项目把“是否更好”作为待检验假设，而不是设计
前提。

OpenCollab 适合实现这项研究，因为它能固定模型、总预算、角色、工具、交接顺序，
并保存 session、trace、token 和终止状态。官方通用 benchmark 可以作为外部参照，
但不直接隔离前端回归状态，且运行成本超出本课程小项目的合理范围。因此本项目
采用固定 React 应用、5 个受控任务、公开测试和隐藏 Playwright 测试组成小型
benchmark。

## 2. 少量直接相关证据

### OpenCollab 自身实验

[OpenCollab 论文](https://arxiv.org/abs/2609.38345)在同一 harness 中比较了
Base 与 Duo。论文的配对结果显示，Duo 在 DeepSWE 的 113 个任务中出现 21 个
“仅 Duo 通过”和 5 个“仅 Base 通过”的任务，差异显著；在 Terminal-Bench 的
89 个任务中则是 6 个“仅 Duo 通过”和 3 个“仅 Base 通过”，差异不显著。
论文同时报告 Duo 的平均 token 明显高于 Base。例如 SWE-bench Pro 为约
6.50M 对 3.89M，DeepSWE 为约 26.11M 对 11.95M。

这组结果支持本项目的实验立场：多 Agent 的收益具有任务依赖性，不能只比较成功
案例，也必须同时报告完成率、耗时和 token。官方 Duo 是“两名 coder 加裁决者”，
与本项目“实现者加回归 QA”机制不同，因此不能把官方结果直接当作本方案有效的
证据。

### 多 Agent 代码审查

[CodeAgent（EMNLP 2024）](https://aclanthology.org/2024.emnlp-main.632/)
把多 Agent 用于代码审查，并设置 QA-Checker 监督不同审查贡献是否回答原问题；
评测覆盖变更与提交信息不一致、漏洞引入、代码风格和修改建议。这说明把实现与
审查拆成不同角色是已有研究问题，而不是为了满足作业形式临时增加角色。

CodeAgent 并未研究 React UI 状态回归，也没有证明同一个模型扮演两个角色一定能
减少回归。我们项目的具体主张仍必须由固定任务、隐藏测试和重复运行来验证。

### 前端任务 benchmark

[SWE-bench Multimodal](https://arxiv.org/abs/2410.03859)包含 617 个来自 17 个
JavaScript UI、图表、可视化和交互地图库的真实任务。这表明前端/视觉软件修复是
独立且真实的 repository-level 评测方向。但它规模较大，关注真实 issue 修复与
视觉输入，不专门测量“新增功能后旧 UI 状态是否回归”。本项目可在后续扩展中选
取其中一两个兼容任务做外部效度检查，不把它作为本轮主实验的必要依赖。

## 3. OpenCollab 是否自带所需 benchmark

OpenCollab 主仓库提供框架、内置 Base/Duo 工作流和研究统计能力；完整的任务准备、
隔离运行与正式评分在独立的
[OpenCollab-Eval 仓库](https://github.com/RISE-X-Lab/OpenCollab-Eval)中。
官方材料主要报告 SWE-bench Pro、Terminal-Bench 2.1 和 DeepSWE。正式 SWE 类
评测需要 Linux、Docker、benchmark 数据和独立 evaluator，不是 clone 主仓库后
直接执行一个小命令就能完成的内置前端测试集。

这些 benchmark 与本项目的关系如下：

| benchmark | 主要能力 | 对本项目的适用性 |
|---|---|---|
| SWE-bench Pro | 真实仓库 issue 修复 | 外部效度强，但昂贵且不聚焦前端回归 |
| Terminal-Bench 2.1 | 终端环境任务 | 可测 Agent 工具能力，不对应 UI 状态机制 |
| DeepSWE | 较复杂软件工程修复 | 可观察多 Agent 收益，但成本很高 |
| SWE-bench Multimodal | JavaScript/视觉软件 issue | 领域最接近，可作为后续扩展 |
| 本项目 5-task suite | 受控 React 状态回归 | 机制隔离最好、成本可控，外部效度有限 |

所以本实验适合在 OpenCollab 上做，但适合的是“用 OpenCollab 编排并记录自定义受控
benchmark”，而不是直接跑完官方大 benchmark。这个选择符合课程要求中的“范围
可控、能够深入分析的小项目”。

## 4. 为什么该设计可能优于单 Agent

设计的核心不是增加一个泛化聊天轮次，而是改变错误搜索方式：

1. Developer 面向当前需求、可见测试和代码实现。
2. QA 只读完整 diff，不重跑 Developer 已执行的公开检查。
3. QA 按键盘路径、取消路径、失败恢复、响应式边界、ARIA 和持久化等旧状态寻找
   Developer 报告中没有覆盖的风险。
4. 只有 QA 给出有 diff 证据的 FAIL 才触发一次修复。

如果 Developer 的失败来自“注意力集中于新需求而遗漏相邻状态”，独立角色提示可能
发现遗漏；如果失败来自模型根本不会实现、两个角色产生高度相关错误，或预算被切分
得太碎，QA 不会有收益。48k 校准 smoke 已显示一个重要负例：在较容易的 T03 上，
Single 和 Dev-QA 都通过，Dev-QA 多用 1,117 token，且多约 13.8 秒。因此正式结论
必须允许“复杂任务改善、简单任务只增加成本”或“整体无改善”。

## 5. 正式实验将回答什么

- H1：在 T03 失败恢复和 T04 响应式边界上，Dev-QA 的完成率是否高于 Single。
- H2：在局部且公开测试较充分的任务上，两者是否同样通过，而 Dev-QA 更慢、更贵。
- H3：每个 QA finding 是否能指向 Developer 未覆盖的 diff 风险，并通过修复前后隐藏
  测试变化证明作用，而不是事后叙述。

5 个任务都运行两种方案；作为关键结论依据的 T03、T04 每种方案各独立运行 3 次。
总计 18 次，单次全局上限 48k，理论最大消耗 864k token。校准数据表明多数无修复
运行约消耗 28k–30k，但困难任务可能接近上限。所有原始运行都保留，不用最佳结果
替代失败结果。

## 6. 局限

- 只有 5 个任务，不能把结果推广为所有前端开发任务。
- 两个角色使用同一 `deepseek-flash`，错误可能相关；本轮不引入第二个模型，以免
  混淆“角色机制”和“模型能力”并增加费用。
- 服务端模型名是别名而非权重哈希，只能通过同一时间窗口运行和保存响应元数据降低
  版本漂移风险。
- 隐藏测试能客观判定行为，但不能覆盖视觉审美；本项目有意研究功能与状态回归，
  不把主观视觉质量作为主要指标。
