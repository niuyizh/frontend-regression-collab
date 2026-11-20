# Results

`raw/<run-id>/` 保存每次正式运行的不可替换证据：

- `agent.json`：条件、预算、耗时和解析后的 workflow 输出；
- `opencollab.log`：CLI 原始输出；
- `opencollab-artifacts/`：会话 transcript、workflow manifest 和 orchestration trace；
- `evaluation.json`：构建、公开/隐藏测试和完整性判定；
- `build.log`、`public-tests.log`、`hidden-tests.log`；
- `hidden-results.json`：Playwright 机器可读原始报告。

运行 `python scripts/summarize_results.py` 后生成：

- `runs.csv`：逐次结果；
- `summary.json`：按条件汇总的真实值。

当前正式实验尚未执行，因此此目录不包含效果数字。工程 smoke 和 oracle 可解性检查不会写入正式结果。

