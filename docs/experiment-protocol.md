# 实验协议

## 1. 假设

- H1：Dev-QA 在包含失败恢复、响应式边界等多状态任务上提高任务完成率和旧功能保持率。
- H2：在局部、公开测试充分的任务上，Dev-QA 的完成率可能与 Single 相同，但耗时更高。
- H3：QA 的收益取决于它能否产生 Developer 未覆盖且可复现的证据；重复执行同一公开测试不构成机制证据。

这些是假设，不是预期结果栏。未完成正式矩阵前不报告提升百分比。

## 2. 固定条件

| 字段 | 值 |
|---|---|
| 框架 | OpenCollab 0.9.6，revision `78ca8e374181f621e70e8d5436199182f8295cbf` |
| 模型 | `deepseek-flash`（DeepSeek V4.1 Flash 服务别名） |
| 协议 | Responses |
| thinking | false（第二轮校准起固定；减少工具任务中的推理开销） |
| reasoning effort | 不适用（thinking=false） |
| 每次全局预算 | 36,000 token；初始 16,000 已被真实 smoke 否决 |
| 并发 | 1 |
| Agent isolation | shared；每次运行使用独立 Git 仓库副本 |
| 前端依赖 | `package-lock.json` 固定 |
| 浏览器 | Playwright 1.65.1 对应 Chromium |
| 运行顺序 | 固定随机种子 20261120 打乱的预注册矩阵 |

服务端模型别名可能在未来指向新权重。本实验通过同一批次连续执行、保存日期、模型列表元数据和响应标识降低这一威胁，但不能提供供应商权重哈希级固定。

## 3. 对照条件

### Single

一个 Frontend Developer 通过状态可见的 `agent_run()` 获得编码工具、任务说明和 36k 全局上限。任务给出主文件但不提供实现答案，两组收到相同提示。Developer 使用 `file_read`、`file_write(str_replace)`、`git_diff` 和只运行固定 build/public suite 的 `verify_frontend`，不提供任意 shell，避免目录漫游和不合规范的 unified diff；自由文本最终报告避免了与代码正确性无关的结构化输出纠正会话。

### Dev-QA

- Developer 使用 `agent_run()`，单次上限 24k。
- Regression QA 使用结构化 verdict，单次上限 8k。
- Repair Developer 使用 `agent_run()`，仅在 QA FAIL 时启动，单次上限 12k。
- Regression QA 始终保持只读工具；读取 Developer 报告与 diff，避免重复已完成检查，聚焦回归面。
- Repair Developer 仅在 QA 返回 FAIL 时运行，最多一轮。

两种条件使用相同的 36k 全局上限。三个角色顺序共享总池，所以 24k/8k/12k 是各调用上限而不是可同时花费的 44k；后续调用会被全局剩余额度进一步截断。Dev-QA 在 QA PASS 时不会为了用满预算而运行无意义修复。

## 4. 任务

| ID | 核心变化 | 重点回归面 | 类型 |
|---|---|---|---|
| T01 | 实时任务搜索 | 选择状态、清除焦点、空结果 | 正常+状态 |
| T02 | 模态框编辑优先级 | Escape、取消、焦点恢复 | 键盘/边界 |
| T03 | 同步失败重试 | loading/error/success、计时器、选择状态 | 失败恢复 |
| T04 | Reports 导航与 active state | 移动菜单、桌面恢复、ARIA | 响应式边界 |
| T05 | 截止日期校验 | 过去日期、草稿恢复、成功清理 | 校验/持久化 |

Agent 工作区只包含固定应用、公开测试和任务说明；`evaluator/` 不复制进去。隐藏测试不会作为提示或工具输出提供给 Agent。

## 5. 运行矩阵

所有 5 个任务在两个条件各运行一次，共 10 次。支撑核心机制结论且更受随机性影响的 T03、T04 在每个条件补到 3 次，增加 8 次，总计 18 次。

```text
5 tasks × 2 conditions × 1 = 10
2 key tasks × 2 conditions × 2 additional repetitions = 8
total = 18
```

T01、T02、T05 的单次结果用于覆盖面和失败案例描述，不用于声称稳定的细粒度差异。正式统计必须保留每次结果，不用最佳一次替换失败运行。

## 6. 评分

一次运行的 `task_complete=true` 需要同时满足：

1. `npm run build` 成功；
2. 6 个公开回归测试全部成功；
3. 对应任务的 2 个隐藏测试全部成功；
4. Agent 未修改公开测试、Playwright 配置或 `package.json`。

记录字段：

- task completion（二元）；
- public regression pass（二元）；
- hidden passed / expected；
- Agent wall-clock seconds；
- evaluation seconds；
- OpenCollab `ctx.tokens_spent()`；
- changed paths、diff、完整命令日志；
- QA verdict、findings、是否触发 repair；
- agent failures 和 OpenCollab orchestration trace。

## 7. 分析

- 全部任务：分别报告两个条件的原始完成数和完成率，不对 5 个异质任务做夸大的显著性结论。
- T03/T04：列出每个重复的完成、token 和耗时，并报告均值、范围和逐任务波动。
- 失败分析：区分新需求未完成、旧功能回归、构建失败、测试篡改、模型/工具失败和框架运行失败。
- QA 有效性：逐条核对 finding 是否有复现证据，以及 repair 是否解决对应评分失败。

## 8. 开跑门槛

- [x] API Key 鉴权成功且 `deepseek-flash` 可见。
- [x] 固定依赖已安装并锁定。
- [x] 固定应用构建通过。
- [x] 公开测试通过。
- [x] 每项隐藏测试在未实现基线处失败。
- [x] 五项 oracle 最小解均能通过构建、公开与隐藏测试。
- [x] OpenCollab 发现自定义 workflow。
- [x] 运行矩阵默认 dry-run，付费调用需要 `--execute`。
- [x] 执行首个 Single 真实预算 smoke 并审计轨迹：16k 在实现前停止，详见 `failure-cases.md`。
- [x] 修订并冻结待 smoke 验证的公平总预算与角色调用上限。
- [ ] 在修订预算下执行一对 Single/Dev-QA smoke。
- [ ] smoke 通过后执行正式 18-run 矩阵。
