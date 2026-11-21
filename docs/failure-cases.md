# 失败案例

## FC-01：16k 预算下的结构化 coding session 提前停止

日期：2026-11-20  
任务：T03  
条件：Single  
模型：`deepseek-flash`，Responses，reasoning effort `low`  
实验性质：预算校准，不计入正式对照

### 观察

Developer 完成三步源码检查但尚未编辑。前两次后续模型调用分别累计报告 3,352 和 4,552 token；会话累计消耗 10,250 token。剩余 5,750 token 时，OpenCollab 停止下一次调用：

```text
budget exhausted before model call: conservative input reservation requires
7827 of 5750 remaining tokens, leaving no output headroom
```

结构化输出恢复会话随后也因需要 6,219 token、仅剩 5,750 token 而立即停止。最终结果为：

```json
{
  "developer": null,
  "tokens_spent": 10250,
  "diff": "",
  "agent_failures": []
}
```

外部评分显示 build 和 6 个公开测试通过，但任务隐藏测试只有 1/2 通过，因为没有产生实现。

### 归因

- 实验配置问题：16k 对该模型、工具集和结构化输出流程不足，不能将失败解释为 Single 能力不足。
- 项目实现问题：初版 workflow 未验证 `ctx.agent()` 返回值，错误地输出 `status=ok`。现已增加 `None`/非字典检查，并停止后续角色。
- 框架设计局限候选：两个子会话均以 budget terminal reason 停止，但 `ctx.agent_failures` 为空，顶层 `workflow.json` 记录 `status=completed`、`reason=null`。自动实验仅查看顶层状态时会误收无效运行。

### 后续

1. 不继续运行原 16k 矩阵。
2. 用最小离线模型复现状态传播行为，确认是否已有同类 issue。
3. 重新校准公平预算和角色切分，再更新预注册协议。

## FC-02：36k 状态可见 Single 在首次编辑失败后耗尽预算

实验性质：第二轮预算与工具协议校准，不计入正式对照。

结果：Developer 运行 7 step、消耗 31,350 token，最终状态为 `stopped`，无代码 diff；构建和公开回归测试因原始 fixture 正常而通过，隐藏测试 1/2。

轨迹显示的因果链：

1. 第 2 次调用错误切换到任务仓库外的绝对目录，读取失败；第 4 次调用再次整文件读取。
2. 每轮累计输入从 2,032 增长到 6,408 token；7 次调用的总用量按重复输入累计。
3. 第 7 次已形成与验收目标一致的实现方向，但向 `apply_patch` 发送了没有行号的裸 `@@` hunk，且未设置 `normalize_hunks=true`，编辑被工具拒绝。
4. 剩余 4,650 token 小于下一次模型调用所需的 10,896 token 保守输入预留，无法纠正补丁格式。

分类：模型/工具适配与实验配置问题，不作为新的框架 bug。OpenCollab 正确把 `agent_run()` 标记为 `stopped`，证明状态可见 API 能防止误收该结果。

协议修订：关闭 thinking；任务提示加入主文件；明确禁止离开当前工作目录；要求第三次响应前首次编辑；Developer 写工具从 `apply_patch` 改为更易稳定调用的 `file_write(str_replace)`；最大 step 从 12 降到 8。修订后仍需一次 Single smoke，未通过前不运行 Dev-QA。

修订后的 36k Single 随后成功：28,218 token、8 step，构建、6/6 公开测试和 2/2 隐藏测试通过。

## FC-03：24k Developer 子上限在正确实现后阻止 QA 启动

实验性质：Dev-QA 角色切分校准，不计入正式对照。

结果：Developer 在 5 step、19,186 token 时已经写出通过构建、全部公开测试和 2/2 隐藏测试的实现；但剩余 4,814 token 小于下一调用所需的 8,979 token 输入预留，`agent_run` 返回 stopped，工作流按协议没有启动 QA。

分类：角色预算配置错误，不是框架问题或模型能力失败。状态传播和外部有效性门槛正确拒绝了该运行。

协议修订：两组共同全局上限改为 48k；Dev-QA 的 Developer/QA/Repair 调用上限改为 30k/6k/18k。QA 直接审查任务、Developer 报告与完整 diff，只做一次无工具调用，不重复公开测试或仓库探索；这样将 token 留给真正的独立审查和必要修复。
4. 正式汇总器只接受 `agent_run_valid=true` 的运行。

完整原始轨迹保留在本地忽略目录 `runs/calibration/`，提交 issue 前仅导出脱敏的最小复现和必要日志。
