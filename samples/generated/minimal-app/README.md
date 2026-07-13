# minimal-app

Generated with explicit modules: foundation

## Development

```console
uv sync --dev
uv run ruff check .
uv run pytest
```

## CLI

- `minimal_app version`
- `minimal_app check`

## Selected Adapters

- None; Foundation and core CLI only.

## Remote Data Boundary

- Fake and local filesystem Adapters do not send data outside the process.
- No remote Adapter is selected in this project.

No remote Adapter is included; generation and tests do not send requests.
