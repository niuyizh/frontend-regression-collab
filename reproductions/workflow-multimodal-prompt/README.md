# Workflow multimodal prompt reproduction

Validated against OpenCollab 0.9.6 at commit
`78ca8e374181f621e70e8d5436199182f8295cbf` with Python 3.13.9.

Run from the OpenCollab checkout:

```bash
uv run python \
  /path/to/frontend-regression-collab/reproductions/workflow-multimodal-prompt/reproduce.py
```

The reproduction makes no network or model call. It demonstrates that the
Responses adapter converts an `image_url` block to `input_image`, while the
public workflow `agent_run()` rejects the same content before building a
session because it requires `prompt` to be a non-empty string.

Expected: workflow authors can pass the provider-neutral text/image content
blocks already supported by the Responses adapter.

Actual:

```json
{
  "responses_adapter_accepts_image": true,
  "workflow_agent_run_accepts_image": false,
  "actual_error": "prompt must be a non-empty string"
}
```
