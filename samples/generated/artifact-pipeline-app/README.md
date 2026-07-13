# artifact-pipeline-app

Generated with explicit modules: artifacts, pipeline, sqlite-artifacts

## Development

```console
uv sync --dev
uv run ruff check .
uv run pytest
```

## CLI

- `artifact_pipeline_app version`
- `artifact_pipeline_app check`

## Selected Adapters

- None; Foundation and core CLI only.

## Remote Data Boundary

- Fake and local filesystem Adapters do not send data outside the process.
- No remote Adapter is selected in this project.

No remote Adapter is included; generation and tests do not send requests.
