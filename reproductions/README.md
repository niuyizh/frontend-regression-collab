# Framework issue reproductions

正式实验后，只把有源码、日志和最小复现支持的 OpenCollab 问题放在这里。每个复现应记录：

- OpenCollab revision、Python/OS 和模型端点；
- 触发条件、最小命令和最小源码；
- 预期行为、实际行为和项目影响；
- 脱敏日志；
- 为什么它是框架问题或设计局限，而不是模型能力或项目配置错误；
- 已有 issue 检索结果和最终 issue 链接；
- 改进方案、代价、回归测试和前后对比。

当前复现：

- `budget-terminal-status/`：真实 16k 校准触发、离线脚本可重复的 schema-bound
  child budget-stop 状态丢失问题。Issue 草稿见 `docs/issue-draft.md`。
