"""Deterministic, file-based project assembly without plugin discovery."""

from __future__ import annotations

import shutil
import tomllib
from collections.abc import Mapping
from pathlib import Path
from textwrap import dedent, indent

import agent_ready_python
from agent_ready_python.assembly.models import (
    AdapterSelectionInput,
    AdapterSpec,
    AssemblyError,
    AssemblyPlan,
    ModuleSpec,
    PresetSpec,
    normalize_adapter_selections,
)

_BASE_FILES = (
    "__init__.py",
    "foundation",
    "interfaces/__init__.py",
    "interfaces/cli/__init__.py",
    "interfaces/cli/common.py",
    "interfaces/cli/core.py",
)
_PRESET_FIELDS = frozenset({"id", "description", "modules", "adapters"})
_MAX_PACKAGE_NAME_LENGTH = 31


def _installed_package_root() -> Path:
    package_file = getattr(agent_ready_python, "__file__", None)
    if package_file is None:
        raise AssemblyError("agent_ready_python package location is unavailable")
    return Path(package_file).resolve().parent


def _default_modules_dir() -> Path:
    return _installed_package_root() / "catalog" / "modules"


def _default_presets_dir() -> Path:
    return _installed_package_root() / "catalog" / "presets"


def _as_strings(value: object, field: str, path: Path) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AssemblyError(f"{path}: {field} must be a list of strings")
    return tuple(value)


def _adapter_specs(raw: object, path: Path) -> tuple[AdapterSpec, ...]:
    if not isinstance(raw, list):
        raise AssemblyError(f"{path}: adapters must be a list")

    result: list[AdapterSpec] = []
    seen: set[str] = set()
    for value in raw:
        if not isinstance(value, dict):
            raise AssemblyError(f"{path}: each adapter must be a table")
        adapter_id = value.get("id")
        if not isinstance(adapter_id, str) or not adapter_id.strip():
            raise AssemblyError(f"{path}: adapter id must be a non-empty string")
        adapter_id = adapter_id.strip()
        if adapter_id in seen:
            raise AssemblyError(f"{path}: duplicate adapter id: {adapter_id}")
        seen.add(adapter_id)
        result.append(
            AdapterSpec(
                id=adapter_id,
                python_dependencies=_as_strings(
                    value.get("python_dependencies", []),
                    "adapter dependencies",
                    path,
                ),
                files=_as_strings(value.get("files", []), "adapter files", path),
                env_example=_as_strings(
                    value.get("env_example", []),
                    "adapter env_example",
                    path,
                ),
            )
        )
    return tuple(result)


def _load_modules(modules_dir: Path) -> dict[str, ModuleSpec]:
    result: dict[str, ModuleSpec] = {}
    for path in sorted(modules_dir.glob("*/module.toml")):
        try:
            with path.open("rb") as stream:
                raw = tomllib.load(stream)
            if not isinstance(raw, dict):
                raise AssemblyError(f"invalid module description: {path}")
            module_id = raw.get("id")
            if not isinstance(module_id, str) or not module_id.strip():
                raise AssemblyError(f"{path}: id must be a non-empty string")
            module_id = module_id.strip()
            if module_id in result:
                raise AssemblyError(f"{path}: duplicate module id: {module_id}")
            adapters = _adapter_specs(raw.get("adapters", []), path)
            adapter_ids = {adapter.id for adapter in adapters}
            has_default = "default_adapter" in raw
            default_adapter = raw.get("default_adapter")
            if not adapters:
                if has_default:
                    raise AssemblyError(
                        f"{path}: default_adapter is invalid for a module without adapters"
                    )
                default_adapter = None
            elif has_default:
                if not isinstance(default_adapter, str) or not default_adapter.strip():
                    raise AssemblyError(f"{path}: default_adapter must be a non-empty string")
                default_adapter = default_adapter.strip()
                if default_adapter not in adapter_ids:
                    raise AssemblyError(
                        f"{path}: default_adapter is not a declared adapter: {default_adapter}"
                    )
            else:
                raise AssemblyError(f"{path}: missing default_adapter")
            result[module_id] = ModuleSpec(
                id=module_id,
                kind=raw.get("kind", "feature"),
                requires=_as_strings(raw.get("requires", []), "requires", path),
                optional=_as_strings(raw.get("optional", []), "optional", path),
                conflicts=_as_strings(raw.get("conflicts", []), "conflicts", path),
                python_dependencies=_as_strings(
                    raw.get("python_dependencies", []), "python_dependencies", path
                ),
                files=_as_strings(raw.get("files", []), "files", path),
                env_example=_as_strings(raw.get("env_example", []), "env_example", path),
                adapters=adapters,
                source=path.parent,
                default_adapter=default_adapter,
            )
        except (TypeError, tomllib.TOMLDecodeError) as exc:
            raise AssemblyError(f"invalid module description: {path}") from exc
    if not result:
        raise AssemblyError(f"no module.toml files found in {modules_dir}")
    return result


def resolve_modules(
    selected: list[str] | tuple[str, ...], modules_dir: Path
) -> tuple[ModuleSpec, ...]:
    """Return selected modules plus required dependencies in deterministic order."""
    specs = _load_modules(modules_dir)
    requested = list(dict.fromkeys(selected))
    unknown = sorted(set(requested) - specs.keys())
    if unknown:
        raise AssemblyError(f"unknown module(s): {', '.join(unknown)}")

    visiting: set[str] = set()
    resolved: list[str] = []

    def visit(module_id: str) -> None:
        if module_id in visiting:
            raise AssemblyError(f"dependency cycle involving {module_id}")
        if module_id in resolved:
            return
        visiting.add(module_id)
        for dependency in specs[module_id].requires:
            if dependency not in specs:
                raise AssemblyError(f"module {module_id} requires unknown module {dependency}")
            visit(dependency)
        visiting.remove(module_id)
        resolved.append(module_id)

    for module_id in requested:
        visit(module_id)

    chosen = set(resolved)
    conflicts = sorted(
        {
            f"{module_id} conflicts with {conflict}"
            for module_id in resolved
            for conflict in specs[module_id].conflicts
            if conflict in chosen
        }
    )
    if conflicts:
        raise AssemblyError("module conflict: " + "; ".join(conflicts))
    return tuple(specs[module_id] for module_id in resolved)


def resolve_adapters(
    specs: tuple[ModuleSpec, ...],
    selections: AdapterSelectionInput | None = None,
) -> dict[str, AdapterSpec]:
    """Resolve one Adapter for every selected module that declares adapters."""

    normalized = normalize_adapter_selections(selections)
    selected_modules = {spec.id for spec in specs}
    explicit = {selection.module: selection.adapter for selection in normalized}
    for selection in normalized:
        if selection.module not in selected_modules:
            raise AssemblyError(
                f"adapter selected for unselected module: {selection.module}"
            )

    result: dict[str, AdapterSpec] = {}
    for spec in specs:
        declared = {adapter.id: adapter for adapter in spec.adapters}
        if not declared:
            if spec.id in explicit:
                raise AssemblyError(f"module {spec.id} has no adapters")
            continue

        default_adapter = spec.default_adapter
        if default_adapter is None:
            raise AssemblyError(f"module {spec.id} is missing default_adapter")
        if default_adapter not in declared:
            raise AssemblyError(
                f"module {spec.id} has invalid default_adapter: {default_adapter}"
            )

        adapter_id = explicit.get(spec.id, default_adapter)
        adapter = declared.get(adapter_id)
        if adapter is None:
            raise AssemblyError(f"unknown adapter for module {spec.id}: {adapter_id}")
        result[spec.id] = adapter
    return result


def _preset_strings(value: object, field: str, path: Path) -> tuple[str, ...]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise AssemblyError(f"{path}: {field} must be a list of strings")
    result: list[str] = []
    seen: set[str] = set()
    for item in value:
        item = item.strip()
        if not item:
            raise AssemblyError(f"{path}: {field} must contain non-empty strings")
        if item in seen:
            raise AssemblyError(f"{path}: duplicate module in preset: {item}")
        seen.add(item)
        result.append(item)
    return tuple(result)


def _load_preset_file(path: Path) -> PresetSpec:
    try:
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise AssemblyError(f"invalid preset description: {path}") from exc
    if not isinstance(raw, dict):
        raise AssemblyError(f"invalid preset description: {path}")

    unknown = sorted(set(raw) - _PRESET_FIELDS)
    if unknown:
        raise AssemblyError(f"{path}: unknown preset field(s): {', '.join(unknown)}")
    missing = sorted(_PRESET_FIELDS - set(raw))
    if missing:
        raise AssemblyError(f"{path}: missing preset field(s): {', '.join(missing)}")

    preset_id = raw["id"]
    description = raw["description"]
    if not isinstance(preset_id, str) or not preset_id.strip():
        raise AssemblyError(f"{path}: id must be a non-empty string")
    if not isinstance(description, str) or not description.strip():
        raise AssemblyError(f"{path}: description must be a non-empty string")

    adapters = raw["adapters"]
    if not isinstance(adapters, dict):
        raise AssemblyError(f"{path}: adapters must be a table of module to adapter")
    normalized_adapters: dict[str, str] = {}
    for module, adapter in adapters.items():
        if not isinstance(module, str) or not module.strip():
            raise AssemblyError(f"{path}: adapter module must be a non-empty string")
        if not isinstance(adapter, str) or not adapter.strip():
            raise AssemblyError(f"{path}: adapter value must be a non-empty string")
        normalized_module = module.strip()
        if normalized_module in normalized_adapters:
            raise AssemblyError(f"{path}: duplicate adapter module: {normalized_module}")
        normalized_adapters[normalized_module] = adapter.strip()

    return PresetSpec(
        id=preset_id,
        description=description,
        modules=_preset_strings(raw["modules"], "modules", path),
        adapters=normalized_adapters,
        source=path,
    )


def _read_presets(presets_dir: Path) -> tuple[PresetSpec, ...]:
    presets_dir = Path(presets_dir)
    if not presets_dir.is_dir():
        raise AssemblyError(f"preset directory does not exist: {presets_dir}")
    paths = sorted(presets_dir.glob("*.toml"))
    if not paths:
        raise AssemblyError(f"no preset TOML files found in {presets_dir}")

    result: list[PresetSpec] = []
    seen_ids: set[str] = set()
    for path in paths:
        preset = _load_preset_file(path)
        if preset.id in seen_ids:
            raise AssemblyError(f"duplicate preset id: {preset.id}")
        seen_ids.add(preset.id)
        result.append(preset)
    return tuple(sorted(result, key=lambda preset: preset.id))


def _validate_preset(preset: PresetSpec, modules_dir: Path) -> None:
    """Validate a preset against the same module and Adapter rules as assembly."""
    specs = resolve_modules(preset.modules, modules_dir)
    resolve_adapters(specs, preset.adapters)


def load_presets(
    presets_dir: Path | None = None,
    modules_dir: Path | None = None,
) -> tuple[PresetSpec, ...]:
    """Load and validate all static presets in deterministic ID order."""
    presets = _read_presets(presets_dir or _default_presets_dir())
    module_path = Path(modules_dir) if modules_dir is not None else _default_modules_dir()
    for preset in presets:
        _validate_preset(preset, module_path)
    return presets


def list_presets(
    presets_dir: Path | None = None,
    modules_dir: Path | None = None,
) -> tuple[PresetSpec, ...]:
    """List validated static presets in deterministic ID order."""
    return load_presets(presets_dir, modules_dir)


def resolve_preset(
    preset_id: str,
    presets_dir: Path | None = None,
    modules_dir: Path | None = None,
) -> PresetSpec:
    """Resolve and validate one static preset by ID."""
    if not isinstance(preset_id, str) or not preset_id.strip():
        raise AssemblyError("preset id must not be empty")
    for preset in load_presets(presets_dir, modules_dir):
        if preset.id == preset_id.strip():
            return preset
    raise AssemblyError(f"unknown preset: {preset_id}")


def resolve_assembly(
    selected: list[str] | tuple[str, ...] = (),
    *,
    preset: str | None = None,
    modules_dir: Path | None = None,
    presets_dir: Path | None = None,
    adapters: AdapterSelectionInput | None = None,
) -> AssemblyPlan:
    """Resolve and validate one complete assembly without writing files."""
    module_path = Path(modules_dir) if modules_dir is not None else _default_modules_dir()
    preset_path = Path(presets_dir) if presets_dir is not None else _default_presets_dir()
    requested = tuple(selected)
    merged_adapters: dict[str, str] = {}
    if preset is not None:
        preset_spec = resolve_preset(preset, preset_path, module_path)
        requested = preset_spec.modules + requested
        merged_adapters.update(preset_spec.adapters)

    for selection in normalize_adapter_selections(adapters):
        merged_adapters[selection.module] = selection.adapter

    specs = resolve_modules(requested, module_path)
    selected_adapters = resolve_adapters(specs, merged_adapters)
    return AssemblyPlan(modules=specs, adapters=selected_adapters)


def _package_name(destination: Path) -> str:
    package = destination.name.replace("-", "_")
    if not package or not package.isidentifier():
        raise AssemblyError(
            f"destination name is not a valid Python package name: {destination.name!r}"
        )
    if len(package) > _MAX_PACKAGE_NAME_LENGTH:
        raise AssemblyError(
            "generated Python package name must be at most "
            f"{_MAX_PACKAGE_NAME_LENGTH} characters"
        )
    return package


def _copy_source(source: Path, target: Path, package: str) -> None:
    """Copy files recursively, replacing imports only in Python files."""
    if source.is_dir():
        for child in source.iterdir():
            if child.name == "__pycache__":
                continue
            _copy_source(child, target / child.name, package)
        return
    if source.suffix in {".pyc", ".pyo"}:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if source.suffix == ".py":
        content = source.read_text(encoding="utf-8")
        target.write_text(content.replace("agent_ready_python", package), encoding="utf-8")
    else:
        shutil.copy2(source, target)


def assemble_project(
    destination: Path,
    selected: list[str] | tuple[str, ...] = (),
    *,
    preset: str | None = None,
    modules_dir: Path | None = None,
    presets_dir: Path | None = None,
    adapters: AdapterSelectionInput | None = None,
    assembly_plan: AssemblyPlan | None = None,
) -> tuple[str, ...]:
    """Generate a normal editable project and return its selected module IDs."""
    plan = assembly_plan
    if plan is None:
        plan = resolve_assembly(
            selected,
            preset=preset,
            modules_dir=modules_dir,
            presets_dir=presets_dir,
            adapters=adapters,
        )
    specs = plan.modules
    selected_adapters = plan.adapters
    root = destination.resolve()
    if root.exists() and any(root.iterdir()):
        raise AssemblyError(f"destination must be empty: {root}")
    package = _package_name(root)
    supported = {"fake", "openai-compatible"}
    for module_id in ("llm-text", "embeddings"):
        adapter = selected_adapters.get(module_id)
        if adapter is not None and adapter.id not in supported:
            raise AssemblyError(f"unsupported generated {module_id} adapter: {adapter.id}")
    source_root = _installed_package_root()

    files = list(_BASE_FILES)
    for spec in specs:
        files.extend(spec.files)
        selected_adapter = selected_adapters.get(spec.id)
        if selected_adapter is not None:
            files.extend(selected_adapter.files)
    ids = {spec.id for spec in specs}
    if {"retrieval", "embeddings"} <= ids:
        files.append("features/retrieval/semantic.py")
    for relative in dict.fromkeys(files):
        source = source_root / relative
        if not source.exists():
            raise AssemblyError(f"assembly file does not exist: {relative}")
    root.mkdir(parents=True, exist_ok=True)
    target_root = root / "src" / package
    target_root.mkdir(parents=True)
    for relative in dict.fromkeys(files):
        source = source_root / relative
        _copy_source(source, target_root / relative, package)
    _write_generated_files(root, package, specs, selected_adapters)
    return tuple(spec.id for spec in specs)


def _bootstrap(
    package: str,
    ids: set[str],
    selected_adapters: Mapping[str, AdapterSpec],
) -> str:
    lines = ['"""Explicit composition root for selected modules."""', ""]
    if not {"retrieval", "embeddings", "llm-text"} & ids:
        return "\n".join((*lines, "", "def build_application() -> None:", "    return None", ""))

    lines.extend(
        [
            "from collections.abc import Iterator",
            "from contextlib import contextmanager",
            "",
        ]
    )
    local_imports: list[str] = []
    if "llm-text" in ids:
        adapter_id = selected_adapters["llm-text"].id
        if adapter_id == "fake":
            local_imports.append(
                f"from {package}.adapters.fake.text_generator import FakeTextGenerator"
            )
        elif adapter_id == "openai-compatible":
            local_imports.append(
                f"from {package}.adapters.openai_compatible import "
                "OpenAICompatibleTextGenerator"
            )
        else:
            raise AssemblyError(f"unsupported generated llm-text adapter: {adapter_id}")
        local_imports.extend(
            [
                f"from {package}.contracts import TextGenerator",
                f"from {package}.features.text_generation import TextGenerationSettings",
            ]
        )
    if "embeddings" in ids:
        adapter_id = selected_adapters["embeddings"].id
        if adapter_id == "fake":
            local_imports.append(
                f"from {package}.adapters.fake.embeddings import FakeEmbeddingProvider"
            )
        elif adapter_id == "openai-compatible":
            local_imports.append(
                f"from {package}.adapters.openai_compatible_embeddings import (\n"
                "    OpenAICompatibleEmbeddingProvider,\n"
                ")"
            )
        else:
            raise AssemblyError(f"unsupported generated embeddings adapter: {adapter_id}")
        local_imports.extend(
            [
                f"from {package}.features.embeddings import EmbeddingSettings",
            ]
        )
        if "llm-text" in ids:
            local_imports.remove(f"from {package}.contracts import TextGenerator")
            local_imports.append(
                f"from {package}.contracts import EmbeddingProvider, TextGenerator"
            )
        else:
            local_imports.append(f"from {package}.contracts import EmbeddingProvider")
    if "retrieval" in ids:
        local_imports.extend(
            [
                f"from {package}.features.documents import DocumentChunk",
                f"from {package}.features.retrieval import KeywordRetriever, Retriever",
            ]
        )
        if "embeddings" in ids:
            local_imports.append(
                f"from {package}.features.retrieval.semantic import SemanticRetriever"
            )
    lines.extend(sorted(local_imports))
    if "llm-text" in ids:
        adapter_id = selected_adapters["llm-text"].id
        lines.extend(
            [
                "",
                "",
                "@contextmanager",
                "def text_generator(settings: TextGenerationSettings) -> Iterator[TextGenerator]:",
                '    """Build exactly the Adapter selected during project generation."""',
            ]
        )
        if adapter_id == "fake":
            lines.extend(
                [
                    '    if settings.provider != "fake":',
                    '        raise ValueError("generated project requires the fake provider")',
                    "    yield FakeTextGenerator(settings.fake_response)",
                ]
            )
        else:
            lines.extend(
                [
                    '    if settings.provider != "openai_compatible":',
                    "        raise ValueError(",
                    '            "generated project requires the openai-compatible provider"',
                    "        )",
                    "    with OpenAICompatibleTextGenerator(settings) as generator:",
                    "        yield generator",
                ]
            )
    if "embeddings" in ids:
        adapter_id = selected_adapters["embeddings"].id
        lines.extend(
            [
                "",
                "",
                "@contextmanager",
                "def embedding_provider(",
                "    settings: EmbeddingSettings",
                ") -> Iterator[EmbeddingProvider]:",
                '    """Build and own the selected embedding Adapter."""',
            ]
        )
        if adapter_id == "fake":
            lines.extend(
                [
                    '    if settings.provider != "fake":',
                    "        raise ValueError(",
                    '            "generated project requires the fake embedding provider"',
                    "        )",
                    "    yield FakeEmbeddingProvider()",
                ]
            )
        else:
            lines.extend(
                [
                    '    if settings.provider != "openai_compatible":',
                    "        raise ValueError(",
                    '            "generated project requires the openai-compatible "',
                    '            "embedding provider"',
                    "        )",
                    "    with OpenAICompatibleEmbeddingProvider(settings) as provider:",
                    "        yield provider",
                ]
            )
    if "retrieval" in ids:
        lines.extend(
            [
                "",
                "",
                "@contextmanager",
                "def document_retriever(",
            ]
        )
        if "embeddings" in ids:
            lines.extend(
                [
                    "    chunks: tuple[DocumentChunk, ...], settings: EmbeddingSettings",
                    ") -> Iterator[Retriever]:",
                    '    """Use keyword retrieval unless semantic mode is enabled."""',
                    "    if not settings.enabled:",
                    "        yield KeywordRetriever(chunks)",
                    "        return",
                    "    with embedding_provider(settings) as provider:",
                    "        yield SemanticRetriever(chunks, provider)",
                ]
            )
        else:
            lines.extend(
                [
                    "    chunks: tuple[DocumentChunk, ...],",
                    ") -> Iterator[Retriever]:",
                    '    """Use deterministic local keyword retrieval."""',
                    "    yield KeywordRetriever(chunks)",
                ]
            )
    return "\n".join((*lines, ""))


def _retrieval_cli(package: str, embeddings_selected: bool) -> str:
    embedding_import = (
        f"        from {package}.features.embeddings import load_embedding_settings\n"
        if embeddings_selected
        else ""
    )
    retrieval_check = (
        "    embedding_settings = load_embedding_settings(selected_env)\n"
        "except ValidationError as exc:\n"
        "    fail_for_error(exc)\n"
        "    return\n\n"
        'typer.echo(f"Chunk size: {document_settings.chunk_size}")\n'
        'typer.echo(f"Chunk overlap: {document_settings.chunk_overlap}")\n'
        'typer.echo(\n'
        '    f"Retrieval mode: {\'semantic\' if embedding_settings.enabled else \'keyword\'}"\n'
        ')\n'
        "if embedding_settings.enabled:\n"
        '    typer.echo(f"Embedding provider: {embedding_settings.provider}")\n'
        '    typer.echo(f"Embedding model: {embedding_settings.model}")'
        if embeddings_selected
        else (
            "except ValidationError as exc:\n"
            "    fail_for_error(exc)\n"
            "    return\n\n"
            'typer.echo(f"Chunk size: {document_settings.chunk_size}")\n'
            'typer.echo(f"Chunk overlap: {document_settings.chunk_overlap}")\n'
            'typer.echo("Retrieval mode: keyword")'
        )
    )
    retrieval_check = indent(retrieval_check, " " * 16)
    search_settings = (
        " " * 20 + "embedding_settings = load_embedding_settings(selected_env)\n"
        if embeddings_selected
        else ""
    )
    retriever_call = (
        "document_retriever(chunks, embedding_settings)"
        if embeddings_selected
        else "document_retriever(chunks)"
    )
    return dedent(
        f'''\
        """CLI commands for documents and local retrieval."""

        from pathlib import Path
        from typing import Annotated

        import typer
        from pydantic import ValidationError

        from {package}.adapters.filesystem import load_text_document
        from {package}.bootstrap import document_retriever
        from {package}.features.documents import TextChunker, load_document_settings
{embedding_import}        from {package}.features.retrieval import RetrievalService
        from {package}.foundation import AppError
        from {package}.interfaces.cli.common import fail_for_error, resolve_env_file


        def register_retrieval_commands(app: typer.Typer) -> None:
            @app.command("retrieval-check")
            def retrieval_check(
                env_file: Annotated[Path | None, typer.Option()] = None,
            ) -> None:
                """Validate retrieval configuration without using a provider."""

                selected_env = resolve_env_file(env_file)
                try:
                    document_settings = load_document_settings(selected_env)
{retrieval_check}

            @app.command()
            def search(
                document: Annotated[Path, typer.Argument()],
                query: Annotated[str, typer.Argument()],
                top_k: Annotated[int, typer.Option(min=1, max=20)] = 3,
                env_file: Annotated[Path | None, typer.Option()] = None,
            ) -> None:
                """Search one text document locally by default."""

                selected_env = resolve_env_file(env_file)
                try:
                    document_settings = load_document_settings(selected_env)
{search_settings}                    loaded = load_text_document(
                        document, document_settings.max_file_bytes
                    )
                    chunks = TextChunker(document_settings).split(loaded)
                    with {retriever_call} as retriever:
                        matches = RetrievalService(retriever).search(query, top_k)
                except (AppError, ValidationError) as exc:
                    fail_for_error(exc)
                    return

                if not matches:
                    typer.echo("No matching chunks")
                    return
                for match in matches:
                    typer.echo(
                        f"[{{match.score:.3f}}] {{match.chunk.source_name}}:"
                        f"{{match.chunk.start}}-{{match.chunk.end}}"
                    )
                    typer.echo(match.chunk.text)
        '''
    )


def _text_generation_settings(adapter_id: str) -> str:
    if adapter_id == "fake":
        return dedent(
            '''\
            """Settings for the selected offline text-generation Adapter."""

            from pathlib import Path
            from typing import Any, Literal

            from pydantic import field_validator
            from pydantic_settings import BaseSettings, SettingsConfigDict


            class TextGenerationSettings(BaseSettings):
                provider: Literal["fake"] = "fake"
                model: str = "fake"
                fake_response: str = "Fake provider response"

                model_config = SettingsConfigDict(
                    env_prefix="AI_LLM_",
                    env_file=None,
                    extra="ignore",
                )

                @field_validator("model", "fake_response")
                @classmethod
                def validate_non_empty(cls, value: str) -> str:
                    value = value.strip()
                    if not value:
                        raise ValueError("value must not be empty")
                    return value


            def load_text_generation_settings(
                env_file: Path | None = None,
                **overrides: Any,
            ) -> TextGenerationSettings:
                return TextGenerationSettings(_env_file=env_file, **overrides)
            '''
        )
    if adapter_id == "openai-compatible":
        return dedent(
            '''\
            """Settings for the selected OpenAI-compatible text Adapter."""

            from pathlib import Path
            from typing import Any, Literal

            from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
            from pydantic_settings import BaseSettings, SettingsConfigDict


            class TextGenerationSettings(BaseSettings):
                provider: Literal["openai_compatible"] = "openai_compatible"
                api_key: SecretStr | None = None
                auth_mode: Literal["bearer", "none"] = "bearer"
                base_url: AnyHttpUrl = "https://api.openai.com/v1"  # type: ignore[assignment]
                model: str = "gpt-4o-mini"
                timeout_seconds: float = Field(default=60.0, gt=0, le=600)
                max_retries: int = Field(default=2, ge=0, le=5)

                model_config = SettingsConfigDict(
                    env_prefix="AI_LLM_",
                    env_file=None,
                    extra="ignore",
                )

                @field_validator("model")
                @classmethod
                def validate_model(cls, value: str) -> str:
                    value = value.strip()
                    if not value:
                        raise ValueError("model must not be empty")
                    return value


            def load_text_generation_settings(
                env_file: Path | None = None,
                **overrides: Any,
            ) -> TextGenerationSettings:
                return TextGenerationSettings(_env_file=env_file, **overrides)
            '''
        )
    raise AssemblyError(f"unsupported generated llm-text adapter: {adapter_id}")


def _embedding_settings(adapter_id: str) -> str:
    if adapter_id == "fake":
        return dedent(
            '''\
            """Settings for the selected offline embedding Adapter."""

            from pathlib import Path
            from typing import Any, Literal

            from pydantic import field_validator
            from pydantic_settings import BaseSettings, SettingsConfigDict


            class EmbeddingSettings(BaseSettings):
                enabled: bool = False
                provider: Literal["fake"] = "fake"
                model: str = "sha256-8"

                model_config = SettingsConfigDict(
                    env_prefix="AI_EMBEDDING_",
                    env_file=None,
                    extra="ignore",
                )

                @field_validator("model")
                @classmethod
                def validate_model(cls, value: str) -> str:
                    value = value.strip()
                    if not value:
                        raise ValueError("embedding model must not be empty")
                    return value


            def load_embedding_settings(
                env_file: Path | None = None,
                **overrides: Any,
            ) -> EmbeddingSettings:
                return EmbeddingSettings(_env_file=env_file, **overrides)
            '''
        )
    if adapter_id == "openai-compatible":
        return dedent(
            '''\
            """Settings for the selected OpenAI-compatible embedding Adapter."""

            from pathlib import Path
            from typing import Any, Literal

            from pydantic import AnyHttpUrl, Field, SecretStr, field_validator
            from pydantic_settings import BaseSettings, SettingsConfigDict


            class EmbeddingSettings(BaseSettings):
                enabled: bool = False
                provider: Literal["openai_compatible"] = "openai_compatible"
                api_key: SecretStr | None = None
                auth_mode: Literal["bearer", "none"] = "bearer"
                base_url: AnyHttpUrl = "https://api.openai.com/v1"  # type: ignore[assignment]
                model: str = "text-embedding-3-small"
                timeout_seconds: float = Field(default=30.0, gt=0, le=600)
                max_retries: int = Field(default=1, ge=0, le=5)

                model_config = SettingsConfigDict(
                    env_prefix="AI_EMBEDDING_",
                    env_file=None,
                    extra="ignore",
                )

                @field_validator("model")
                @classmethod
                def validate_model(cls, value: str) -> str:
                    value = value.strip()
                    if not value:
                        raise ValueError("embedding model must not be empty")
                    return value


            def load_embedding_settings(
                env_file: Path | None = None,
                **overrides: Any,
            ) -> EmbeddingSettings:
                return EmbeddingSettings(_env_file=env_file, **overrides)
            '''
        )
    raise AssemblyError(f"unsupported generated embeddings adapter: {adapter_id}")


def _text_generation_cli(package: str, adapter_id: str) -> str:
    if adapter_id == "fake":
        provider_status = 'typer.echo("API key: not required")'
    elif adapter_id == "openai-compatible":
        provider_status = """typer.echo(f"Base URL: {settings.base_url}")
if settings.auth_mode == "none":
    typer.echo("API key: not required")
else:
    typer.echo(f"API key: {'configured' if settings.api_key else 'missing'}")"""
    else:
        raise AssemblyError(f"unsupported generated llm-text adapter: {adapter_id}")
    provider_status = indent(provider_status, " " * 16)
    return dedent(
        f'''\
        """CLI commands for the selected text-generation Adapter."""

        from pathlib import Path
        from typing import Annotated

        import typer
        from pydantic import ValidationError

        from {package}.application import AskService
        from {package}.bootstrap import text_generator
        from {package}.features.text_generation import load_text_generation_settings
        from {package}.foundation import AppError
        from {package}.interfaces.cli.common import fail_for_error, resolve_env_file


        def register_text_generation_commands(app: typer.Typer) -> None:
            @app.command("llm-check")
            def llm_check(
                env_file: Annotated[Path | None, typer.Option()] = None,
            ) -> None:
                """Validate text-generation configuration without contacting a provider."""

                selected_env = resolve_env_file(env_file)
                try:
                    settings = load_text_generation_settings(selected_env)
                except ValidationError as exc:
                    fail_for_error(exc)
                    return

                typer.echo(f"Provider: {{settings.provider}}")
                typer.echo(f"Model: {{settings.model}}")
{provider_status}

            @app.command()
            def ask(
                prompt: Annotated[str, typer.Argument()],
                env_file: Annotated[Path | None, typer.Option()] = None,
            ) -> None:
                """Generate one non-streaming text response."""

                selected_env = resolve_env_file(env_file)
                try:
                    settings = load_text_generation_settings(selected_env)
                    with text_generator(settings) as generator:
                        result = AskService(generator).ask(prompt)
                except (AppError, ValidationError) as exc:
                    fail_for_error(exc)
                    return
                except ValueError as exc:
                    typer.echo(f"Error: {{exc}}", err=True)
                    raise typer.Exit(code=2) from exc

                typer.echo(result.text)
        '''
    )


def _smoke_tests(
    package: str,
    ids: set[str],
    selected_adapters: Mapping[str, AdapterSpec],
) -> str:
    lines = [
        "from typer.testing import CliRunner",
        "",
        f"from {package}.interfaces.cli.app import app",
        "",
        "runner = CliRunner()",
        "",
        "",
        "def test_version() -> None:",
        '    result = runner.invoke(app, ["version"])',
        "    assert result.exit_code == 0",
        '    assert result.stdout.strip() == "0.1.0"',
        "",
        "",
        "def test_check() -> None:",
        '    result = runner.invoke(app, ["check"])',
        "    assert result.exit_code == 0",
        '    assert "Python: OK" in result.stdout',
    ]
    if "retrieval" in ids:
        lines.extend(
            [
                "",
                "",
                "def test_local_search(tmp_path) -> None:",
                '    document = tmp_path / "notes.txt"',
                '    document.write_text("offline needle content", encoding="utf-8")',
                '    result = runner.invoke(app, ["search", str(document), "needle"])',
                "    assert result.exit_code == 0",
                '    assert "needle" in result.stdout',
            ]
        )
    if "llm-text" in ids and selected_adapters["llm-text"].id == "fake":
        lines.extend(
            [
                "",
                "",
                "def test_fake_ask() -> None:",
                '    result = runner.invoke(app, ["ask", "hello"])',
                "    assert result.exit_code == 0",
                '    assert result.stdout.strip() == "Fake provider response"',
            ]
        )
    elif "llm-text" in ids:
        lines.extend(
            [
                "",
                "",
                "def test_selected_remote_provider_is_reported_without_request() -> None:",
                '    result = runner.invoke(app, ["llm-check"])',
                "    assert result.exit_code == 0",
                '    assert "Provider: openai_compatible" in result.stdout',
            ]
        )
    return "\n".join(lines) + "\n"


def _write_generated_files(
    root: Path,
    package: str,
    specs: tuple[ModuleSpec, ...],
    selected_adapters: Mapping[str, AdapterSpec],
) -> None:
    ids = {spec.id for spec in specs}
    selected_files: set[str] = set()
    for spec in specs:
        selected_files.update(spec.files)
        selected_adapter = selected_adapters.get(spec.id)
        if selected_adapter is not None:
            selected_files.update(selected_adapter.files)
    if {"retrieval", "embeddings"} <= ids:
        selected_files.add("features/retrieval/semantic.py")
    dependencies = {"pydantic-settings>=2.0,<3", "typer>=0.12,<1"}
    env_example = ["AI_LOG_LEVEL=INFO"]
    for spec in specs:
        dependencies.update(spec.python_dependencies)
        env_example.extend(spec.env_example)
        selected_adapter = selected_adapters.get(spec.id)
        if selected_adapter is not None:
            dependencies.update(selected_adapter.python_dependencies)
            env_example.extend(selected_adapter.env_example)

    bootstrap = _bootstrap(package, ids, selected_adapters)

    app_lines = [
        f"from {package}.interfaces.cli.core import (\n"
        "    create_core_cli,\n"
        ")"
    ]
    registrations = []
    if "retrieval" in ids:
        app_lines.append(
            f"from {package}.interfaces.cli.retrieval import (\n"
            "    register_retrieval_commands,\n"
            ")"
        )
        registrations.append("register_retrieval_commands(app)")
    if "llm-text" in ids:
        app_lines.append(
            f"from {package}.interfaces.cli.text_generation import (\n"
            "    register_text_generation_commands,\n"
            ")"
        )
        registrations.append("register_text_generation_commands(app)")
    if "interfaces/cli/pipeline.py" in selected_files:
        app_lines.append(
            f"from {package}.interfaces.cli.pipeline import (\n"
            "    register_pipeline_commands,\n"
            ")"
        )
        registrations.append("register_pipeline_commands(app)")
    app = "\n".join(sorted(app_lines)) + "\n\napp = create_core_cli()\n"
    if registrations:
        app += "\n".join(registrations) + "\n"
    app += "\ndef main() -> None:\n    app()\n"

    project_name = root.name
    script_name = project_name.replace("-", "_")
    dependency_lines = "".join(f'    "{dependency}",\n' for dependency in sorted(dependencies))
    pyproject = f'''\
[project]
name = "{project_name}"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
{dependency_lines}]

[project.scripts]
{script_name} = "{package}.interfaces.cli.app:main"

[dependency-groups]
dev = [
    "pytest>=8,<9",
    "ruff>=0.6",
]

[build-system]
requires = ["hatchling>=1.27"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/{package}"]

[tool.pytest.ini_options]
addopts = "-q"
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B", "SIM"]
'''
    commands = ["version", "check"]
    if "retrieval" in ids:
        commands.append("search <document> <query>")
    if "llm-text" in ids:
        commands.extend(["llm-check", "ask <prompt>"])
    command_lines = "\n".join(f"- `{script_name} {command}`" for command in commands)
    adapter_lines = [
        f"- `{module_id}`: `{selected_adapters[module_id].id}`"
        for module_id in sorted(selected_adapters)
    ]
    remote_boundaries = [
        "- Fake and local filesystem Adapters do not send data outside the process.",
    ]
    llm_adapter = selected_adapters.get("llm-text")
    if llm_adapter is not None and llm_adapter.id == "openai-compatible":
        remote_boundaries.append(
            "- `llm-text` sends prompts only when `ask` is invoked with the generated "
            "OpenAI-compatible Adapter and its configured credentials."
        )
    embedding_adapter = selected_adapters.get("embeddings")
    if embedding_adapter is not None and embedding_adapter.id == "openai-compatible":
        remote_boundaries.append(
            "- `embeddings` sends document chunks and queries only when semantic retrieval "
            "is enabled and search is invoked."
        )
    if not any("sends" in line for line in remote_boundaries):
        remote_boundaries.append("- No remote Adapter is selected in this project.")
    selected_adapter_text = "\n".join(adapter_lines) or "- None; Foundation and core CLI only."
    remote_boundary_text = "\n".join(remote_boundaries)
    remote_note = (
        "OpenAI-compatible code is included only when selected during assembly. "
        "Generation and tests do not send requests."
        if any("sends" in line for line in remote_boundaries)
        else "No remote Adapter is included; generation and tests do not send requests."
    )
    generated: dict[str, str] = {
        "bootstrap.py": bootstrap,
        "interfaces/cli/app.py": app,
        "__main__.py": f"from {package}.interfaces.cli.app import main\n\nmain()\n",
        "pyproject.toml": pyproject,
        "README.md": (
            f"# {project_name}\n\n"
            f"Generated with explicit modules: {', '.join(sorted(ids)) or 'foundation'}\n\n"
            "## Development\n\n"
            "```console\nuv sync --dev\nuv run ruff check .\nuv run pytest\n```\n\n"
            "## CLI\n\n"
            f"{command_lines}\n"
            "\n## Selected Adapters\n\n"
            f"{selected_adapter_text}\n"
            "\n## Remote Data Boundary\n\n"
            f"{remote_boundary_text}\n"
            f"\n{remote_note}\n"
        ),
        ".env.example": "\n".join(dict.fromkeys(env_example)) + "\n",
        ".gitignore": ".env\n.venv/\n__pycache__/\n",
        "tests/test_smoke.py": _smoke_tests(package, ids, selected_adapters),
    }
    if "retrieval" in ids:
        generated["interfaces/cli/retrieval.py"] = _retrieval_cli(package, "embeddings" in ids)
    if "llm-text" in ids:
        llm_adapter_id = selected_adapters["llm-text"].id
        generated["features/text_generation/settings.py"] = _text_generation_settings(
            llm_adapter_id
        )
        generated["interfaces/cli/text_generation.py"] = _text_generation_cli(
            package, llm_adapter_id
        )
    if "embeddings" in ids:
        generated["features/embeddings/settings.py"] = _embedding_settings(
            selected_adapters["embeddings"].id
        )
    if "embeddings" in ids or "llm-text" in ids:
        contract_lines = ['"""Contracts selected for this generated application."""', ""]
        exports: list[str] = []
        if "embeddings" in ids:
            contract_lines.append("from .embeddings import EmbeddingProvider, EmbeddingResult")
            exports.extend(["EmbeddingProvider", "EmbeddingResult"])
        if "llm-text" in ids:
            contract_lines.append(
                "from .text_generation import TextGenerationRequest, "
                "TextGenerationResult, TextGenerator"
            )
            exports.extend(["TextGenerationRequest", "TextGenerationResult", "TextGenerator"])
        contract_lines.extend(["", "__all__ = ["])
        contract_lines.extend(f"    {name!r}," for name in exports)
        contract_lines.append("]\n")
        generated["contracts/__init__.py"] = "\n".join(contract_lines)

    for relative, content in generated.items():
        target = root / relative
        if relative.endswith(".py") and not relative.startswith("tests/"):
            target = root / "src" / package / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
