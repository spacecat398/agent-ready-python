# llm-app

Generated with explicit modules: llm-text

## Development

```console
uv sync --dev
uv run ruff check .
uv run pytest
```

## CLI

- `llm_app version`
- `llm_app check`
- `llm_app llm-check`
- `llm_app ask <prompt>`

## Selected Adapters

- `llm-text`: `fake`

## Remote Data Boundary

- Fake and local filesystem Adapters do not send data outside the process.
- No remote Adapter is selected in this project.

No remote Adapter is included; generation and tests do not send requests.
