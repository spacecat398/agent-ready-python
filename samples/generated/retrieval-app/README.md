# retrieval-app

Generated with explicit modules: documents, embeddings, retrieval

## Development

```console
uv sync --dev
uv run ruff check .
uv run pytest
```

## CLI

- `retrieval_app version`
- `retrieval_app check`
- `retrieval_app search <document> <query>`

## Selected Adapters

- `documents`: `filesystem`
- `embeddings`: `fake`

## Remote Data Boundary

- Fake and local filesystem Adapters do not send data outside the process.
- No remote Adapter is selected in this project.

No remote Adapter is included; generation and tests do not send requests.
