# Agent-ready Python

A modular Python starter for AI applications. The current validation profile includes a small
foundation, text generation, strict text documents, local retrieval, optional embeddings,
explicit composition roots, a CLI, and offline tests.

## Setup

```bash
uv sync
uv run pytest
uv run ruff check .
uv run ai-app version
uv run ai-app check
uv run ai-app llm-check
uv run ai-app ask "Hello"
uv run ai-app retrieval-check
uv run ai-app search path/to/document.txt "search terms"
uv run ai-app pipeline-check
```

The default Adapter is the offline `fake` Adapter, so setup and tests do not require an API key or
network access. Copy `.env.example` to `.env` only when local configuration is needed. Existing
`.env` files must never be overwritten or committed.

## Adapter Selection

The assembler accepts one repeated `--adapter MODULE=ADAPTER` option for each selected module:

```bash
uv run create-ai-app llm-app --add llm-text
uv run create-ai-app remote-llm --add llm-text --adapter llm-text=openai-compatible
uv run create-ai-app mixed-adapters-app --add retrieval --add embeddings --add llm-text \
  --adapter llm-text=fake --adapter embeddings=openai-compatible
```

Every selected module with Adapters receives exactly one choice. Omitting a choice uses the
module's safe offline `default_adapter`. The generated project contains only the selected Adapter's
source, dependencies, and environment example. OpenAI-compatible projects include the code and
configuration needed for a request, but assembly and generated tests never send one.

Document search uses the local filesystem and keyword retrieval by default. Semantic retrieval is
enabled only when `AI_EMBEDDING_ENABLED=true`; document chunks and queries are then sent to the
selected embedding Adapter. Embedding credentials are independent and never inherit the
text-generation API key. A generated project includes only the selected remote Adapter source,
dependencies, and placeholder configuration; it never creates or copies `.env`.

Artifact and Pipeline modules are optional. Stage outputs are immutable and persisted before the
next stage runs. Producing a valid replacement does not activate it automatically; applications
must explicitly update an active-artifact slot.

## Create a project

The offline assembler reads the packaged static descriptors under
`src/agent_ready_python/catalog/modules/`, resolves required dependencies, validates presets under
`src/agent_ready_python/catalog/presets/`, and writes an ordinary Python project with an explicit
bootstrap and CLI. These catalog files and the source copied by the assembler are included in the
installed `agent-ready-python` package, so `create-ai-app` does not depend on the repository root or
current working directory after installation. List the available presets without choosing a
destination:

```bash
uv run create-ai-app --list-presets
uv run create-ai-app new-project --preset minimal
uv run create-ai-app rag-app --preset rag-local
uv run create-ai-app text-app --preset text-cli
uv run create-ai-app pipeline-app --preset artifact-pipeline
```

The built-in presets are:

- `minimal`: Foundation and core CLI only;
- `text-cli`: `llm-text` with the offline `fake` Adapter;
- `rag-local`: `retrieval` plus `embeddings`, with `documents=filesystem` and
  `embeddings=fake`;
- `artifact-pipeline`: `pipeline` plus `sqlite-artifacts`, including the required `artifacts`
  dependency and no remote capability.

The legacy `retrieval` preset remains available as a static compatibility preset for existing
assembly commands.

Preset modules are resolved together with their required dependency closure. Repeated `--add`
options extend that module selection. Preset Adapter choices are used first; an explicit
`--adapter MODULE=ADAPTER` for the same module overrides the preset choice. Duplicate explicit
assignments remain an error, and every preset is validated against its own module closure before
`--add` modules are considered. Invalid presets never create the destination directory.

The destination must be empty. The assembler creates `.env.example` from the selected modules but
never creates or overwrites `.env`. Generated projects do not discover modules at runtime.

## Release-candidate validation

Version `0.1.0` is a release candidate and has not been published to PyPI. The local validation
builds both distribution formats, installs the wheel into an isolated environment, and runs the
installed generator without using the source checkout:

```console
uv sync --locked
uv run ruff check .
uv run pytest
uv build

mapfile -t wheels < <(find dist -maxdepth 1 -type f -name '*.whl' -print)
test "${#wheels[@]}" -eq 1
wheel="${wheels[0]}"
validation_root="$(mktemp -d)"
trap 'rm -rf "$validation_root"' EXIT
uv venv "$validation_root/wheel-venv"
uv pip install --python "$validation_root/wheel-venv/bin/python" "$wheel"
(
  cd "$validation_root"
  "$validation_root/wheel-venv/bin/create-ai-app" --list-presets
  "$validation_root/wheel-venv/bin/create-ai-app" "$validation_root/minimal" --preset minimal
  "$validation_root/wheel-venv/bin/create-ai-app" "$validation_root/rag-local" --preset rag-local
)
uv sync --directory "$validation_root/minimal" --dev
uv run --directory "$validation_root/minimal" pytest
uv sync --directory "$validation_root/rag-local" --dev
uv run --directory "$validation_root/rag-local" pytest
test ! -e "$validation_root/minimal/.env"
test ! -e "$validation_root/rag-local/.env"
```

See the [changelog](CHANGELOG.md) and [release checklist](RELEASE_CHECKLIST.md) for the current
release-candidate scope and the maintainer confirmations still required before publication.

## Generated samples

Independent generated projects are kept under `samples/generated/`:

- `minimal-app` -> `minimal`: Foundation and core CLI only;
- `llm-app` -> `text-cli`: text generation with the offline `fake` Adapter, including runnable
  Fake `ask`;
- `retrieval-app` -> `rag-local`: documents with the `filesystem` Adapter, local retrieval, and
  the `fake` embedding Adapter; semantic mode is disabled by default and has no remote dependency;
- `artifact-pipeline-app` -> `artifact-pipeline`: immutable artifacts, validated pipeline stages,
  and the local `sqlite-artifacts` Adapter, with no AI Provider;
- `mixed-adapters-app`: Phase 6 Adapter-selection sample with `filesystem` documents, local
  retrieval, Fake text generation, and the `openai-compatible` embedding Adapter; it includes
  `httpx`, but embedding requests require explicit semantic enablement.

Each sample has its own `pyproject.toml`, smoke tests, and explicit composition root. Run
`uv sync --dev`, `uv run ruff check .`, and `uv run pytest` from the sample directory to verify it
without depending on this repository's package environment.

Architecture: [`modular-architecture-design.md`](modular-architecture-design.md)

Progress: [`PROGRESS.md`](PROGRESS.md)

## License

This project is licensed under the [MIT License](LICENSE).
