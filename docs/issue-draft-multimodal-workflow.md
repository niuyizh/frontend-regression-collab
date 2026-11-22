# OpenCollab issue draft: workflow `agent_run()` cannot start multimodal sessions

## Summary

OpenCollab's OpenAI Responses adapter preserves `image_url` content blocks and
converts them to `input_image`, but the public workflow API only accepts
`agent_run(prompt: str)`. Passing provider-neutral text/image blocks is rejected
with `ValueError: prompt must be a non-empty string` before a session is built.

This prevents authored workflows from supplying screenshots to a fresh role,
even when the selected endpoint and model support image input. It affected a
DesignBench React workflow in which Developer and Regression QA need to inspect
UI screenshots.

## Environment

- OpenCollab 0.9.6
- Commit: `78ca8e374181f621e70e8d5436199182f8295cbf`
- Python 3.13.9
- Linux x86_64
- Reproduction is provider-independent and makes no network call

## Minimal reproduction

From the OpenCollab checkout:

```bash
uv run python \
  /path/to/frontend-regression-collab/reproductions/workflow-multimodal-prompt/reproduce.py
```

Observed output:

```json
{
  "responses_adapter_accepts_image": true,
  "workflow_agent_run_accepts_image": false,
  "actual_error": "prompt must be a non-empty string"
}
```

## Source analysis

1. `opencollab/adapters/llm/responses_provider.py` already converts
   `image_url` content to Responses `input_image`.
2. `opencollab/workflows.py` declares `WorkflowContext.agent_run(prompt: str)`.
3. `opencollab/application/workflow_agent_run.py` explicitly rejects every
   non-string prompt before `_build_workflow_session()`.
4. `opencollab/bootstrap/agent_runtime.py::_run_session()` also types the prompt
   as `str` and forwards it through `session.add_user_message(prompt)`.

This is a workflow API capability gap, not a model failure or project
configuration error. The configured DeepSeek account in the motivating project
also lacks a vision model, but the offline reproduction establishes the API
limitation independently of that endpoint.

## Expected behavior

`WorkflowContext.agent_run()` should accept a documented provider-neutral user
content type, for example `str | Sequence[TextBlock | ImageURLBlock]`, and pass
it unchanged to `session.add_user_message()`. Unsupported providers or models
should return a capability error rather than the workflow layer rejecting all
structured content.

## Suggested change

- Introduce and export a shared `UserContent` type.
- Extend `WorkflowContext.agent_run`, `WorkflowAgentRunMixin.agent_run`,
  `_build_workflow_session`, `_run_session_turn`, and `run_agent` to accept it.
- Preserve the existing non-empty-string validation for string prompts and add
  validation for a non-empty list of supported content blocks.
- Add an end-to-end Responses contract test asserting that an authored workflow
  delivers `input_text` plus `input_image` to the borrowed LLM.

## Benefits and trade-offs

Benefit: workflows can run visual software-engineering, document, chart, and
multimodal benchmark tasks without encoding provider-specific requests.

Trade-off: the public type surface expands, token estimation must continue to
handle image blocks, and Chat/Anthropic adapters need either equivalent
conversion or an explicit capability error.

## Existing issue search

Checked all standalone issues returned by the GitHub API and searched the
repository issue index for `multimodal`, `image_url`, `input_image`, `vision`,
and `agent_run` on 2026-11-22. No same-topic issue was found. The repository
currently returned no standalone issues; numbered items were pull requests.
