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
4. 正式汇总器只接受 `agent_run_valid=true` 的运行。

完整原始轨迹保留在本地忽略目录 `runs/calibration/`，提交 issue 前仅导出脱敏的最小复现和必要日志。

