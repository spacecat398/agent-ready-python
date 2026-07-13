# mixed-adapters-app

Generated with explicit modules: documents, embeddings, llm-text, retrieval

## Development

```console
uv sync --dev
uv run ruff check .
uv run pytest
```

## CLI

- `mixed_adapters_app version`
- `mixed_adapters_app check`
- `mixed_adapters_app search <document> <query>`
- `mixed_adapters_app llm-check`
- `mixed_adapters_app ask <prompt>`

## Selected Adapters

- `documents`: `filesystem`
- `embeddings`: `openai-compatible`
- `llm-text`: `fake`

## Remote Data Boundary

- Fake and local filesystem Adapters do not send data outside the process.
- `embeddings` sends document chunks and queries only when semantic retrieval is enabled and search is invoked.

OpenAI-compatible code is included only when selected during assembly. Generation and tests do not send requests.
