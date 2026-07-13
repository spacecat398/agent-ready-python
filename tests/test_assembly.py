import ast
import importlib
import json
import subprocess
import tomllib
from pathlib import Path

import pytest
from typer.testing import CliRunner

import agent_ready_python
from agent_ready_python.assembly import (
    AdapterSelection,
    AdapterSpec,
    AssemblyError,
    AssemblyPlan,
    ModuleSpec,
    PresetSpec,
    assemble_project,
    list_presets,
    load_presets,
    parse_adapter_selections,
    resolve_adapters,
    resolve_assembly,
    resolve_modules,
    resolve_preset,
)

PROJECT_ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = Path(agent_ready_python.__file__).resolve().parent
MODULES_DIR = PACKAGE_ROOT / "catalog" / "modules"
PRESETS_DIR = PACKAGE_ROOT / "catalog" / "presets"
ORIGINAL_PACKAGE = "agent_ready_python"


def _module(
    path: Path,
    module_id: str,
    *,
    requires: tuple[str, ...] = (),
    conflicts: tuple[str, ...] = (),
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    (path / "module.toml").write_text(
        "\n".join(
            (
                f'id = "{module_id}"',
                'kind = "feature"',
                f"requires = {json.dumps(list(requires))}",
                "optional = []",
                f"conflicts = {json.dumps(list(conflicts))}",
                "python_dependencies = []",
                "files = []",
            )
        ),
        encoding="utf-8",
    )


def _module_with_adapters(
    path: Path,
    module_id: str,
    *,
    adapters: tuple[str, ...] = ("fake",),
    default_adapter: str = "fake",
    files: tuple[str, ...] = (),
) -> None:
    path.mkdir(parents=True, exist_ok=True)
    lines = [
        f'id = "{module_id}"',
        'kind = "feature"',
        "requires = []",
        "optional = []",
        "conflicts = []",
        "python_dependencies = []",
        f"files = {json.dumps(list(files))}",
        f'default_adapter = "{default_adapter}"',
    ]
    for adapter in adapters:
        lines.extend(
            (
                "",
                "[[adapters]]",
                f'id = "{adapter}"',
                "python_dependencies = []",
                "files = []",
                "env_example = []",
            )
        )
    (path / "module.toml").write_text("\n".join(lines) + "\n", encoding="utf-8")


def _write_preset(
    path: Path,
    *,
    preset_id: str = "demo",
    description: str = "Demo preset",
    modules: tuple[str, ...] = (),
    adapters: dict[str, str] | None = None,
) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        f'id = {json.dumps(preset_id)}',
        f'description = {json.dumps(description)}',
        f"modules = {json.dumps(list(modules))}",
        "",
        "[adapters]",
    ]
    for module, adapter in (adapters or {}).items():
        lines.append(f"{json.dumps(module)} = {json.dumps(adapter)}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_generated_smoke(root: Path) -> None:
    import os

    environment = os.environ.copy()
    current_pythonpath = environment.get("PYTHONPATH")
    pythonpath = str(root / "src")
    if current_pythonpath:
        pythonpath += os.pathsep + current_pythonpath
    environment["PYTHONPATH"] = pythonpath
    result = subprocess.run(
        ["uv", "run", "pytest", str(root / "tests")],
        cwd=PROJECT_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def _generated_package(root: Path) -> tuple[Path, str]:
    project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))
    package = project["tool"]["hatch"]["build"]["targets"]["wheel"]["packages"][0].split("/")[-1]
    return root / "src" / package, package


def _absolute_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.add(node.module)
    return imports


def _assert_generated_project_is_closed(root: Path) -> tuple[Path, str]:
    package_root, package = _generated_package(root)
    python_files = tuple(package_root.rglob("*.py"))
    assert python_files
    for path in python_files:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")
        assert ORIGINAL_PACKAGE not in path.read_text(encoding="utf-8")
        for imported in _absolute_imports(path):
            if imported == package or imported.startswith(f"{package}."):
                relative = imported.split(".")[1:]
                target = package_root.joinpath(*relative)
                assert target.with_suffix(".py").exists() or (target / "__init__.py").exists(), (
                    path,
                    imported,
                )
    return package_root, package


def _assert_generated_smoke_is_offline(root: Path) -> str:
    smoke = (root / "tests" / "test_smoke.py").read_text(encoding="utf-8")
    assert smoke
    assert "httpx" not in smoke
    assert "requests" not in smoke
    assert "socket" not in smoke
    assert "AI_EMBEDDING_ENABLED=true" not in smoke
    return smoke


def _assert_generated_project_lints(root: Path) -> None:
    lint = subprocess.run(
        ["uv", "run", "ruff", "check", str(root)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert lint.returncode == 0, lint.stdout + lint.stderr


def _run_create_ai_app(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["uv", "run", "create-ai-app", *arguments],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def _synthetic_module_spec(
    module_id: str,
    adapters: tuple[AdapterSpec, ...],
    default_adapter: str | None,
) -> ModuleSpec:
    return ModuleSpec(
        id=module_id,
        kind="feature",
        requires=(),
        optional=(),
        conflicts=(),
        python_dependencies=(),
        files=(),
        env_example=(),
        adapters=adapters,
        source=Path("module"),
        default_adapter=default_adapter,
    )


def test_parse_adapter_selections_accepts_repeated_module_assignments() -> None:
    assert parse_adapter_selections(
        (" llm-text = fake ", "embeddings=openai-compatible")
    ) == (
        AdapterSelection(module="llm-text", adapter="fake"),
        AdapterSelection(module="embeddings", adapter="openai-compatible"),
    )


@pytest.mark.parametrize("value", ("llm-text", "llm-text=fake=extra"))
def test_parse_adapter_selections_rejects_invalid_format(value: str) -> None:
    with pytest.raises(AssemblyError, match="MODULE=ADAPTER"):
        parse_adapter_selections((value,))


@pytest.mark.parametrize("value", ("=fake", "llm-text=", " = "))
def test_parse_adapter_selections_rejects_empty_module_or_adapter(value: str) -> None:
    with pytest.raises(AssemblyError, match="MODULE=ADAPTER"):
        parse_adapter_selections((value,))


def test_parse_adapter_selections_rejects_duplicate_modules() -> None:
    with pytest.raises(AssemblyError, match="duplicate adapter selection for module: llm-text"):
        parse_adapter_selections(("llm-text=fake", "llm-text=openai-compatible"))


def test_resolve_modules_closes_dependencies_in_deterministic_order() -> None:
    assert tuple(spec.id for spec in resolve_modules(("retrieval",), MODULES_DIR)) == (
        "documents",
        "retrieval",
    )
    assert tuple(spec.id for spec in resolve_modules(("retrieval", "documents"), MODULES_DIR)) == (
        "documents",
        "retrieval",
    )


def test_resolve_adapters_uses_fake_defaults_and_skips_modules_without_adapters() -> None:
    specs = resolve_modules(
        ("llm-text", "embeddings", "retrieval", "pipeline"),
        MODULES_DIR,
    )

    adapters = resolve_adapters(specs)

    assert adapters["llm-text"].id == "fake"
    assert adapters["embeddings"].id == "fake"
    assert adapters["documents"].id == "filesystem"
    assert {"llm-text", "embeddings", "documents"} == set(adapters)


def test_resolve_adapters_accepts_explicit_openai_compatible_selection() -> None:
    specs = resolve_modules(("llm-text", "embeddings"), MODULES_DIR)

    adapters = resolve_adapters(specs, {"llm-text": "openai-compatible"})

    assert adapters["llm-text"].id == "openai-compatible"
    assert adapters["embeddings"].id == "fake"


def test_resolve_adapters_rejects_selection_for_unselected_module() -> None:
    specs = resolve_modules(("llm-text",), MODULES_DIR)

    with pytest.raises(AssemblyError, match="unselected module: embeddings"):
        resolve_adapters(specs, {"embeddings": "fake"})


def test_resolve_adapters_rejects_selection_for_module_without_adapters() -> None:
    specs = resolve_modules(("pipeline",), MODULES_DIR)

    with pytest.raises(AssemblyError, match="module pipeline has no adapters"):
        resolve_adapters(specs, {"pipeline": "fake"})


def test_resolve_adapters_rejects_unknown_adapter() -> None:
    specs = resolve_modules(("llm-text",), MODULES_DIR)

    with pytest.raises(AssemblyError, match="unknown adapter for module llm-text: missing"):
        resolve_adapters(specs, {"llm-text": "missing"})


def test_resolve_assembly_returns_a_validated_plan_from_the_package_catalog() -> None:
    plan = resolve_assembly(preset="rag-local")

    assert isinstance(plan, AssemblyPlan)
    assert tuple(spec.id for spec in plan.modules) == ("documents", "retrieval", "embeddings")
    assert {module: adapter.id for module, adapter in plan.adapters.items()} == {
        "documents": "filesystem",
        "embeddings": "fake",
    }


def test_default_catalog_apis_are_independent_of_the_current_working_directory(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    assert [preset.id for preset in list_presets()] == [
        "artifact-pipeline",
        "minimal",
        "rag-local",
        "retrieval",
        "text-cli",
    ]
    plan = resolve_assembly(preset="text-cli")

    assert tuple(spec.id for spec in plan.modules) == ("llm-text",)
    assert plan.adapters["llm-text"].id == "fake"


def test_assemble_project_uses_package_sources_when_cwd_is_unrelated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unrelated_cwd = tmp_path / "unrelated-cwd"
    unrelated_cwd.mkdir()
    monkeypatch.chdir(unrelated_cwd)
    destination = tmp_path / "generated-from-installed-pkg"

    assemble_project(destination, preset="minimal")

    package_root, _ = _assert_generated_project_is_closed(destination)
    assert (package_root / "foundation").is_dir()
    assert (package_root / "interfaces/cli/core.py").is_file()


@pytest.mark.parametrize(
    ("default_adapter", "message"),
    (("missing", "invalid default_adapter"), (None, "missing default_adapter")),
)
def test_resolve_adapters_rejects_invalid_or_missing_default_adapter(
    default_adapter: str | None, message: str
) -> None:
    fake = AdapterSpec(id="fake", python_dependencies=(), files=(), env_example=())
    spec = _synthetic_module_spec("demo", (fake,), default_adapter)

    with pytest.raises(AssemblyError, match=message):
        resolve_adapters((spec,))


def test_module_description_rejects_duplicate_adapter_ids(tmp_path: Path) -> None:
    module = tmp_path / "demo"
    module.mkdir()
    (module / "module.toml").write_text(
        """
id = "demo"
kind = "feature"
requires = []
optional = []
conflicts = []
python_dependencies = []
files = []
env_example = []
default_adapter = "fake"

[[adapters]]
id = "fake"
python_dependencies = []
files = []
env_example = []

[[adapters]]
id = "fake"
python_dependencies = []
files = []
env_example = []
""".strip()
        + "\n",
        encoding="utf-8",
    )

    with pytest.raises(AssemblyError, match="duplicate adapter id: fake"):
        resolve_modules(("demo",), tmp_path)


@pytest.mark.parametrize(
    ("modules", "selected", "message"),
    (
        ({"root": ("missing",)}, ("root",), "requires unknown module"),
        ({"a": ("b",), "b": ("a",)}, ("a",), "dependency cycle"),
    ),
)
def test_resolve_modules_rejects_invalid_dependency_graph(
    tmp_path: Path, modules: dict[str, tuple[str, ...]], selected: tuple[str, ...], message: str
) -> None:
    for module_id, requires in modules.items():
        _module(tmp_path / module_id, module_id, requires=requires)
    with pytest.raises(AssemblyError, match=message):
        resolve_modules(selected, tmp_path)


def test_resolve_modules_rejects_unknown_and_conflicting_modules(tmp_path: Path) -> None:
    _module(tmp_path / "safe", "safe", conflicts=("unsafe",))
    _module(tmp_path / "unsafe", "unsafe")
    with pytest.raises(AssemblyError, match="unknown module"):
        resolve_modules(("does-not-exist",), tmp_path)
    with pytest.raises(AssemblyError, match="module conflict"):
        resolve_modules(("safe", "unsafe"), tmp_path)


def test_assemble_rejects_nonempty_destination_and_does_not_copy_or_overwrite_env(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "app"
    destination.mkdir()
    env_file = destination / ".env"
    env_file.write_text("SECRET=do-not-touch", encoding="utf-8")
    with pytest.raises(AssemblyError, match="must be empty"):
        assemble_project(destination, preset="minimal")
    assert env_file.read_text(encoding="utf-8") == "SECRET=do-not-touch"

    fresh = tmp_path / "fresh-app"
    assemble_project(fresh, preset="minimal")
    assert not (fresh / ".env").exists()
    assert (fresh / ".env.example").exists()


@pytest.mark.parametrize("name", ("bad.name", "bad space", "123app"))
def test_assemble_rejects_invalid_package_names(tmp_path: Path, name: str) -> None:
    with pytest.raises(AssemblyError, match="valid Python package name"):
        assemble_project(tmp_path / name, preset="minimal")


def test_assemble_accepts_31_character_package_name_and_lints(tmp_path: Path) -> None:
    destination = tmp_path / "phase-six-openai-text-cli-v2026"
    package_name = destination.name.replace("-", "_")
    assert len(package_name) == 31

    assemble_project(destination, preset="minimal")
    _, package = _assert_generated_project_is_closed(destination)
    assert package == package_name
    _assert_generated_project_lints(destination)


def test_assemble_rejects_32_character_package_name_without_destination(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "phase-six-openai-text-cli-v20260"
    package_name = destination.name.replace("-", "_")
    assert len(package_name) == 32

    with pytest.raises(AssemblyError, match="at most 31 characters"):
        assemble_project(destination, preset="minimal")

    assert not destination.exists()


def test_assemble_converts_hyphenated_project_name_to_importable_package(tmp_path: Path) -> None:
    destination = tmp_path / "my-ai-app"
    assemble_project(destination, preset="minimal")
    package_root, package = _assert_generated_project_is_closed(destination)
    assert package == "my_ai_app"
    assert package_root.exists()
    assert tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))["project"][
        "scripts"
    ]["my_ai_app"] == "my_ai_app.interfaces.cli.app:main"


@pytest.mark.parametrize(
    ("preset", "selected", "forbidden_paths", "forbidden_dependencies"),
    (
        ("minimal", (), ("features", "adapters"), ("httpx",)),
        ("retrieval", (), ("features/embeddings", "semantic.py"), ("embeddings",)),
    ),
)
def test_minimal_and_retrieval_are_pruned_and_closed(
    tmp_path: Path,
    preset: str,
    selected: tuple[str, ...],
    forbidden_paths: tuple[str, ...],
    forbidden_dependencies: tuple[str, ...],
) -> None:
    destination = tmp_path / preset
    assemble_project(destination, selected, preset=preset)
    package_root, _ = _assert_generated_project_is_closed(destination)
    paths = {path.relative_to(package_root).as_posix() for path in package_root.rglob("*")}
    project = tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = "\n".join(project["project"]["dependencies"])
    assert not any(any(forbidden in path for forbidden in forbidden_paths) for path in paths)
    assert not any(forbidden in dependencies for forbidden in forbidden_dependencies)


@pytest.mark.parametrize(
    ("name", "selected", "preset", "required_prefixes", "forbidden_prefixes"),
    (
        (
            "minimal-env",
            (),
            "minimal",
            ("AI_LOG_LEVEL=",),
            ("AI_LLM_", "AI_DOCUMENTS_", "AI_EMBEDDING_"),
        ),
        (
            "retrieval-env",
            (),
            "retrieval",
            ("AI_LOG_LEVEL=", "AI_DOCUMENTS_"),
            ("AI_LLM_", "AI_EMBEDDING_"),
        ),
        (
            "retrieval-embeddings-env",
            ("embeddings",),
            "retrieval",
            ("AI_LOG_LEVEL=", "AI_DOCUMENTS_", "AI_EMBEDDING_"),
            ("AI_LLM_",),
        ),
        (
            "llm-env",
            ("llm-text",),
            None,
            ("AI_LOG_LEVEL=", "AI_LLM_"),
            ("AI_DOCUMENTS_", "AI_EMBEDDING_"),
        ),
    ),
)
def test_generated_env_example_matches_selected_module_configuration(
    tmp_path: Path,
    name: str,
    selected: tuple[str, ...],
    preset: str | None,
    required_prefixes: tuple[str, ...],
    forbidden_prefixes: tuple[str, ...],
) -> None:
    destination = tmp_path / name
    assemble_project(destination, selected, preset=preset)

    env_example = (destination / ".env.example").read_text(encoding="utf-8").splitlines()
    assert len(env_example) == len(set(env_example))
    assert not (destination / ".env").exists()
    assert all(any(line.startswith(prefix) for line in env_example) for prefix in required_prefixes)
    assert not any(
        line.startswith(prefix) for line in env_example for prefix in forbidden_prefixes
    )
    if name == "minimal-env":
        assert env_example == ["AI_LOG_LEVEL=INFO"]


@pytest.mark.parametrize("selected", (("retrieval", "embeddings"), ("llm-text",), ("pipeline",)))
def test_extended_assemblies_compile_and_have_no_stale_imports(
    tmp_path: Path, selected: tuple[str, ...]
) -> None:
    destination = tmp_path / ("generated-" + "-".join(selected))
    assemble_project(destination, selected)
    _assert_generated_project_is_closed(destination)


def test_generated_llm_text_fake_ask_runs_without_installing_generated_project(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "llm-app"
    assemble_project(destination, ("llm-text",))
    _, package = _assert_generated_project_is_closed(destination)
    monkeypatch.syspath_prepend(str(destination / "src"))
    importlib.invalidate_caches()
    app_module = importlib.import_module(f"{package}.interfaces.cli.app")
    result = CliRunner().invoke(app_module.app, ["ask", "hello"])
    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == "Fake provider response"


def test_generated_llm_fake_contains_only_offline_adapter_and_asks_successfully(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "phase6-llm-fake"
    assemble_project(destination, ("llm-text",))
    package_root, package = _assert_generated_project_is_closed(destination)

    assert (package_root / "adapters/fake/text_generator.py").is_file()
    assert not (package_root / "adapters/openai_compatible").exists()

    project = tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = "\n".join(project["project"]["dependencies"])
    assert "httpx" not in dependencies

    env_example = (destination / ".env.example").read_text(encoding="utf-8")
    assert not (destination / ".env").exists()
    assert "AI_LLM_API_KEY" not in env_example
    assert "AI_LLM_BASE_URL" not in env_example
    settings = (package_root / "features/text_generation/settings.py").read_text(encoding="utf-8")
    assert "api_key" not in settings
    assert "base_url" not in settings

    readme = (destination / "README.md").read_text(encoding="utf-8")
    assert "- `llm-text`: `fake`" in readme
    assert "Fake and local filesystem Adapters do not send data outside the process." in readme
    assert "No remote Adapter is selected in this project." in readme
    assert _assert_generated_smoke_is_offline(destination)

    monkeypatch.syspath_prepend(str(destination / "src"))
    importlib.invalidate_caches()
    app_module = importlib.import_module(f"{package}.interfaces.cli.app")
    result = CliRunner().invoke(app_module.app, ["ask", "hello"])

    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == "Fake provider response"


def test_generated_llm_openai_compatible_is_remote_only_and_check_is_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "phase6-llm-openai"
    assemble_project(
        destination,
        ("llm-text",),
        adapters={"llm-text": "openai-compatible"},
    )
    package_root, package = _assert_generated_project_is_closed(destination)

    assert (package_root / "adapters/openai_compatible/text_generator.py").is_file()
    assert not (package_root / "adapters/fake/text_generator.py").exists()

    project = tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = "\n".join(project["project"]["dependencies"])
    assert "httpx>=0.27,<1" in dependencies
    env_example = (destination / ".env.example").read_text(encoding="utf-8")
    assert not (destination / ".env").exists()
    assert "AI_LLM_API_KEY=" in env_example
    assert "AI_LLM_BASE_URL=https://api.openai.com/v1" in env_example
    settings = (package_root / "features/text_generation/settings.py").read_text(encoding="utf-8")
    assert "api_key" in settings
    assert "base_url" in settings

    readme = (destination / "README.md").read_text(encoding="utf-8")
    assert "- `llm-text`: `openai-compatible`" in readme
    assert "`llm-text` sends prompts only when `ask` is invoked" in readme
    assert "Generation and tests do not send requests." in readme
    smoke = _assert_generated_smoke_is_offline(destination)
    assert "test_selected_remote_provider_is_reported_without_request" in smoke
    assert '["ask"' not in smoke

    monkeypatch.syspath_prepend(str(destination / "src"))
    importlib.invalidate_caches()
    app_module = importlib.import_module(f"{package}.interfaces.cli.app")
    result = CliRunner().invoke(app_module.app, ["llm-check"])

    assert result.exit_code == 0, result.stdout
    assert "Provider: openai_compatible" in result.stdout
    assert "API key: missing" in result.stdout


def test_long_hyphenated_openai_llm_cli_is_linted_and_check_runs_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "phase-six-openai-text-cli-v2026"
    assemble_project(
        destination,
        ("llm-text",),
        adapters={"llm-text": "openai-compatible"},
    )
    package_root, package = _assert_generated_project_is_closed(destination)

    app_path = package_root / "interfaces/cli/app.py"
    app_lines = app_path.read_text(encoding="utf-8").splitlines()
    assert all(len(line) <= 100 for line in app_lines)
    assert (package_root / "adapters/openai_compatible/text_generator.py").is_file()
    assert not (package_root / "adapters/fake/text_generator.py").exists()
    _assert_generated_project_lints(destination)

    monkeypatch.syspath_prepend(str(destination / "src"))
    importlib.invalidate_caches()
    app_module = importlib.import_module(f"{package}.interfaces.cli.app")
    result = CliRunner().invoke(app_module.app, ["llm-check"])

    assert result.exit_code == 0, result.stdout
    assert "Provider: openai_compatible" in result.stdout
    assert "API key: missing" in result.stdout


@pytest.mark.parametrize(
    ("adapter_id", "selected_path", "forbidden_path", "remote"),
    (
        (
            "fake",
            "adapters/fake/embeddings.py",
            "adapters/openai_compatible_embeddings",
            False,
        ),
        (
            "openai-compatible",
            "adapters/openai_compatible_embeddings/provider.py",
            "adapters/fake/embeddings.py",
            True,
        ),
    ),
)
def test_generated_retrieval_embeddings_selects_one_adapter_and_keeps_default_search_local(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    adapter_id: str,
    selected_path: str,
    forbidden_path: str,
    remote: bool,
) -> None:
    destination = tmp_path / f"p6-ret-emb-{adapter_id.replace('-', '_')}"
    assemble_project(
        destination,
        ("retrieval", "embeddings"),
        adapters={"embeddings": adapter_id},
    )
    package_root, package = _assert_generated_project_is_closed(destination)

    assert (package_root / "features/retrieval/semantic.py").is_file()
    assert (package_root / selected_path).is_file()
    assert not (package_root / forbidden_path).exists()
    assert not (package_root / "adapters/fake/text_generator.py").exists()
    assert not (package_root / "adapters/openai_compatible/text_generator.py").exists()

    project = tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = "\n".join(project["project"]["dependencies"])
    env_example = (destination / ".env.example").read_text(encoding="utf-8")
    assert not (destination / ".env").exists()
    settings = (package_root / "features/embeddings/settings.py").read_text(encoding="utf-8")
    readme = (destination / "README.md").read_text(encoding="utf-8")
    if remote:
        assert "httpx>=0.27,<1" in dependencies
        assert "AI_EMBEDDING_API_KEY=" in env_example
        assert "AI_EMBEDDING_BASE_URL=https://api.openai.com/v1" in env_example
        assert "api_key" in settings
        assert "base_url" in settings
        assert (
            "`embeddings` sends document chunks and queries only when semantic retrieval"
            in readme
        )
    else:
        assert "httpx" not in dependencies
        assert "AI_EMBEDDING_API_KEY" not in env_example
        assert "AI_EMBEDDING_BASE_URL" not in env_example
        assert "api_key" not in settings
        assert "base_url" not in settings
        assert "No remote Adapter is selected in this project." in readme
    assert f"- `embeddings`: `{adapter_id}`" in readme
    smoke = _assert_generated_smoke_is_offline(destination)
    assert "test_local_search" in smoke

    document = tmp_path / f"{adapter_id.replace('-', '_')}-notes.txt"
    document.write_text("offline needle content", encoding="utf-8")
    monkeypatch.syspath_prepend(str(destination / "src"))
    importlib.invalidate_caches()
    app_module = importlib.import_module(f"{package}.interfaces.cli.app")
    result = CliRunner().invoke(
        app_module.app,
        ["search", str(document), "needle"],
        env={"AI_EMBEDDING_ENABLED": "false"},
    )

    assert result.exit_code == 0, result.stdout
    assert "offline needle content" in result.stdout


@pytest.mark.parametrize(
    ("name", "llm_adapter", "embedding_adapter", "llm_provider", "embedding_provider"),
    (
        (
            "mix-a",
            "fake",
            "openai-compatible",
            "fake",
            "openai_compatible",
        ),
        (
            "mix-b",
            "openai-compatible",
            "fake",
            "openai_compatible",
            "fake",
        ),
    ),
)
def test_generated_mixed_adapters_have_closed_bootstrap_linted_code_and_matching_settings(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    name: str,
    llm_adapter: str,
    embedding_adapter: str,
    llm_provider: str,
    embedding_provider: str,
) -> None:
    destination = tmp_path / name
    assemble_project(
        destination,
        ("llm-text", "embeddings"),
        adapters={"llm-text": llm_adapter, "embeddings": embedding_adapter},
    )
    package_root, package = _assert_generated_project_is_closed(destination)
    _assert_generated_project_lints(destination)

    monkeypatch.syspath_prepend(str(destination / "src"))
    importlib.invalidate_caches()
    bootstrap = importlib.import_module(f"{package}.bootstrap")
    text_settings_module = importlib.import_module(f"{package}.features.text_generation.settings")
    embedding_settings_module = importlib.import_module(f"{package}.features.embeddings.settings")
    assert callable(bootstrap.text_generator)
    assert callable(bootstrap.embedding_provider)
    assert text_settings_module.load_text_generation_settings().provider == llm_provider
    assert embedding_settings_module.load_embedding_settings().provider == embedding_provider

    readme = (destination / "README.md").read_text(encoding="utf-8")
    assert f"- `llm-text`: `{llm_adapter}`" in readme
    assert f"- `embeddings`: `{embedding_adapter}`" in readme
    assert "OpenAI-compatible code is included only when selected during assembly." in readme
    if llm_adapter == "openai-compatible":
        assert "`llm-text` sends prompts only when `ask` is invoked" in readme
    else:
        assert (
            "`embeddings` sends document chunks and queries only when semantic retrieval"
            in readme
        )
    smoke = _assert_generated_smoke_is_offline(destination)
    if llm_adapter == "fake":
        assert "test_fake_ask" in smoke
    else:
        assert "test_selected_remote_provider_is_reported_without_request" in smoke
        assert '["ask"' not in smoke

    assert (package_root / "bootstrap.py").is_file()


@pytest.mark.parametrize(
    ("name", "selected", "preset", "required_smoke", "forbidden_smoke"),
    (
        ("minimal-quality", (), "minimal", ("test_version", "test_check"), ("retrieval", "llm")),
        (
            "retrieval-quality",
            ("retrieval", "embeddings"),
            None,
            ("test_local_search",),
            ("fake_ask",),
        ),
        ("llm-quality", ("llm-text",), None, ("test_fake_ask",), ("local_search",)),
    ),
)
def test_generated_projects_include_independent_quality_tools_and_smoke_tests(
    tmp_path: Path,
    name: str,
    selected: tuple[str, ...],
    preset: str | None,
    required_smoke: tuple[str, ...],
    forbidden_smoke: tuple[str, ...],
) -> None:
    destination = tmp_path / name
    assemble_project(destination, selected, preset=preset)

    project = tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))
    dev_dependencies = set(project["dependency-groups"]["dev"])
    assert any(dependency.startswith("pytest") for dependency in dev_dependencies)
    assert any(dependency.startswith("ruff") for dependency in dev_dependencies)
    assert project["tool"]["pytest"]["ini_options"]["testpaths"] == ["tests"]
    assert project["tool"]["ruff"]["line-length"] == 100
    assert project["tool"]["ruff"]["target-version"] == "py312"
    assert project["tool"]["ruff"]["lint"]["select"]

    smoke = (destination / "tests" / "test_smoke.py").read_text(encoding="utf-8")
    assert smoke
    assert all(marker in smoke for marker in required_smoke)
    assert not any(marker in smoke for marker in forbidden_smoke)

    readme = (destination / "README.md").read_text(encoding="utf-8")
    assert "uv sync --dev" in readme
    assert "uv run ruff check ." in readme
    assert "uv run pytest" in readme


def test_combined_retrieval_embeddings_llm_bootstrap_and_cli_are_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "combined-app"
    assemble_project(destination, ("retrieval", "embeddings", "llm-text"))
    package_root, package = _assert_generated_project_is_closed(destination)

    bootstrap = package_root / "bootstrap.py"
    tree = ast.parse(bootstrap.read_text(encoding="utf-8"))
    function_lines = [
        node.lineno
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    assert function_lines
    first_function_line = min(function_lines)
    assert not any(
        isinstance(node, (ast.Import, ast.ImportFrom)) and node.lineno > first_function_line
        for node in tree.body
    )

    monkeypatch.syspath_prepend(str(destination / "src"))
    importlib.invalidate_caches()
    app_module = importlib.import_module(f"{package}.interfaces.cli.app")
    help_result = CliRunner().invoke(app_module.app, ["--help"])
    assert help_result.exit_code == 0, help_result.stdout
    assert "search" in help_result.stdout
    assert "ask" in help_result.stdout

    lint = subprocess.run(
        ["uv", "run", "ruff", "check", str(destination)],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert lint.returncode == 0, lint.stdout + lint.stderr


def test_pipeline_feature_does_not_require_sqlite_adapter() -> None:
    descriptor = tomllib.loads(
        (MODULES_DIR / "pipeline" / "module.toml").read_text(encoding="utf-8")
    )
    assert "sqlite-artifacts" not in descriptor["requires"]


def test_create_ai_app_cli_accepts_repeated_adapter_options(tmp_path: Path) -> None:
    destination = tmp_path / "phase6-cli-mixed"
    result = _run_create_ai_app(
        str(destination),
        "--add",
        "llm-text",
        "--add",
        "embeddings",
        "--adapter",
        "llm-text=fake",
        "--adapter",
        "embeddings=openai-compatible",
    )

    assert result.returncode == 0, result.stderr
    assert "Created" in result.stdout
    assert "llm-text" in result.stdout
    assert "embeddings" in result.stdout
    package_root, _ = _assert_generated_project_is_closed(destination)
    assert (package_root / "adapters/fake/text_generator.py").is_file()
    assert (package_root / "adapters/openai_compatible_embeddings/provider.py").is_file()
    assert not (package_root / "adapters/openai_compatible/text_generator.py").exists()


def test_create_ai_app_cli_rejects_invalid_adapter_format_without_creating_destination(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "phase6-cli-invalid-format"
    result = _run_create_ai_app(
        str(destination),
        "--add",
        "llm-text",
        "--adapter",
        "not-an-assignment",
    )

    assert result.returncode == 2
    assert "MODULE=ADAPTER" in result.stderr
    assert not destination.exists()


def test_create_ai_app_cli_rejects_adapter_for_unselected_module_without_partial_output(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "phase6-cli-unselected"
    result = _run_create_ai_app(
        str(destination),
        "--add",
        "llm-text",
        "--adapter",
        "embeddings=fake",
    )

    assert result.returncode == 2
    assert "unselected module: embeddings" in result.stderr
    assert not destination.exists()


def test_create_ai_app_cli_rejects_unknown_adapter_without_partial_output(tmp_path: Path) -> None:
    destination = tmp_path / "phase6-cli-unknown"
    result = _run_create_ai_app(
        str(destination),
        "--add",
        "llm-text",
        "--adapter",
        "llm-text=does-not-exist",
    )

    assert result.returncode == 2
    assert "unknown adapter for module llm-text: does-not-exist" in result.stderr
    assert not destination.exists()


def test_create_ai_app_cli_reports_nonempty_destination_and_preserves_existing_files(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "phase6-cli-existing"
    destination.mkdir()
    marker = destination / ".env"
    marker.write_text("SECRET=keep", encoding="utf-8")

    result = _run_create_ai_app(
        str(destination),
        "--add",
        "llm-text",
        "--adapter",
        "llm-text=fake",
    )

    assert result.returncode == 2
    assert "destination must be empty" in result.stderr
    assert marker.read_text(encoding="utf-8") == "SECRET=keep"
    assert not (destination / "src").exists()


def test_preset_spec_normalizes_values_and_freezes_adapters(tmp_path: Path) -> None:
    preset = PresetSpec(
        id=" demo ",
        description=" Demo preset ",
        modules=[" retrieval "],
        adapters={"z-module": "fake", "a-module": "filesystem"},
        source=tmp_path / "demo.toml",
    )

    assert preset.id == "demo"
    assert preset.description == "Demo preset"
    assert preset.modules == ("retrieval",)
    assert tuple(preset.adapters) == ("a-module", "z-module")
    assert dict(preset.adapters) == {
        "a-module": "filesystem",
        "z-module": "fake",
    }
    with pytest.raises(TypeError):
        preset.adapters["new-module"] = "fake"


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("id", "", "preset id must not be empty"),
        ("description", "", "preset description must not be empty"),
        ("modules", ("",), "preset modules must contain non-empty strings"),
        ("adapters", {"": "fake"}, "preset adapter module must not be empty"),
        ("adapters", {"demo": ""}, "preset adapter must not be empty"),
    ),
)
def test_preset_spec_rejects_empty_values(
    tmp_path: Path,
    field: str,
    value: object,
    message: str,
) -> None:
    values: dict[str, object] = {
        "id": "demo",
        "description": "Demo preset",
        "modules": (),
        "adapters": {},
        "source": tmp_path / "demo.toml",
    }
    values[field] = value

    with pytest.raises(AssemblyError, match=message):
        PresetSpec(**values)  # type: ignore[arg-type]


def test_load_presets_is_deterministic_and_contains_all_declared_compositions() -> None:
    expected = {
        "artifact-pipeline": {
            "modules": ("pipeline", "sqlite-artifacts"),
            "adapters": {},
        },
        "minimal": {"modules": (), "adapters": {}},
        "rag-local": {
            "modules": ("retrieval", "embeddings"),
            "adapters": {"documents": "filesystem", "embeddings": "fake"},
        },
        "retrieval": {
            "modules": ("documents", "retrieval"),
            "adapters": {"documents": "filesystem"},
        },
        "text-cli": {
            "modules": ("llm-text",),
            "adapters": {"llm-text": "fake"},
        },
    }

    loaded = load_presets()
    listed = list_presets()
    assert [preset.id for preset in loaded] == sorted(expected)
    assert [preset.id for preset in listed] == [preset.id for preset in loaded]
    assert [preset.source.name for preset in loaded] == [
        f"{preset_id}.toml" for preset_id in sorted(expected)
    ]

    for preset in loaded:
        assert preset.description.strip()
        assert preset.modules == expected[preset.id]["modules"]
        assert dict(preset.adapters) == expected[preset.id]["adapters"]
        with pytest.raises(TypeError):
            preset.adapters["injected"] = "fake"

    assert resolve_preset(" rag-local ") == next(
        preset for preset in loaded if preset.id == "rag-local"
    )


def test_load_presets_rejects_missing_directory_and_empty_directory(tmp_path: Path) -> None:
    with pytest.raises(AssemblyError, match="preset directory does not exist"):
        load_presets(tmp_path / "missing", MODULES_DIR)

    empty = tmp_path / "empty-presets"
    empty.mkdir()
    with pytest.raises(AssemblyError, match="no preset TOML files found"):
        load_presets(empty, MODULES_DIR)


def test_load_presets_rejects_toml_syntax_errors(tmp_path: Path) -> None:
    presets = tmp_path / "presets"
    presets.mkdir()
    (presets / "broken.toml").write_text(
        'id = "broken"\nmodules = [\n',
        encoding="utf-8",
    )

    with pytest.raises(AssemblyError, match="invalid preset description"):
        load_presets(presets, MODULES_DIR)


def test_load_presets_rejects_unknown_fields(tmp_path: Path) -> None:
    presets = tmp_path / "presets"
    _write_preset(presets / "unknown.toml")
    content = (presets / "unknown.toml").read_text(encoding="utf-8")
    content = content.replace("\n[adapters]\n", '\nextra = "not allowed"\n\n[adapters]\n')
    (presets / "unknown.toml").write_text(content, encoding="utf-8")

    with pytest.raises(AssemblyError, match=r"unknown preset field\(s\): extra"):
        load_presets(presets, MODULES_DIR)


@pytest.mark.parametrize("missing", ("id", "description", "modules", "adapters"))
def test_load_presets_rejects_missing_fields(tmp_path: Path, missing: str) -> None:
    presets = tmp_path / "presets"
    presets.mkdir()
    fields = {
        "id": 'id = "demo"\n',
        "description": 'description = "Demo preset"\n',
        "modules": "modules = []\n",
        "adapters": "\n[adapters]\n",
    }
    content = "".join(value for name, value in fields.items() if name != missing)
    (presets / "missing.toml").write_text(content, encoding="utf-8")

    with pytest.raises(AssemblyError, match=rf"missing preset field\(s\): {missing}"):
        load_presets(presets, MODULES_DIR)


@pytest.mark.parametrize(
    ("content", "message"),
    (
        (
            'id = 1\ndescription = "Demo"\nmodules = []\n\n[adapters]\n',
            "id must be a non-empty string",
        ),
        (
            'id = "demo"\ndescription = []\nmodules = []\n\n[adapters]\n',
            "description must be a non-empty string",
        ),
        (
            'id = "demo"\ndescription = "Demo"\nmodules = "retrieval"\n\n[adapters]\n',
            "modules must be a list of strings",
        ),
        (
            'id = "demo"\ndescription = "Demo"\nmodules = []\nadapters = []\n',
            "adapters must be a table of module to adapter",
        ),
    ),
)
def test_load_presets_rejects_wrong_field_types(
    tmp_path: Path, content: str, message: str
) -> None:
    presets = tmp_path / "presets"
    presets.mkdir()
    (presets / "wrong-type.toml").write_text(content, encoding="utf-8")

    with pytest.raises(AssemblyError, match=message):
        load_presets(presets, MODULES_DIR)


@pytest.mark.parametrize(
    ("content", "message"),
    (
        (
            'id = ""\ndescription = "Demo"\nmodules = []\n\n[adapters]\n',
            "id must be a non-empty string",
        ),
        (
            'id = "demo"\ndescription = ""\nmodules = []\n\n[adapters]\n',
            "description must be a non-empty string",
        ),
        (
            'id = "demo"\ndescription = "Demo"\nmodules = [""]\n\n[adapters]\n',
            "modules must contain non-empty strings",
        ),
        (
            'id = "demo"\ndescription = "Demo"\nmodules = []\n\n[adapters]\n"" = "fake"\n',
            "adapter module must be a non-empty string",
        ),
        (
            'id = "demo"\ndescription = "Demo"\nmodules = []\n\n[adapters]\n"demo" = ""\n',
            "adapter value must be a non-empty string",
        ),
    ),
)
def test_load_presets_rejects_empty_values(
    tmp_path: Path, content: str, message: str
) -> None:
    presets = tmp_path / "presets"
    presets.mkdir()
    (presets / "empty-value.toml").write_text(content, encoding="utf-8")

    with pytest.raises(AssemblyError, match=message):
        load_presets(presets, MODULES_DIR)


def test_load_presets_rejects_duplicate_preset_ids(tmp_path: Path) -> None:
    presets = tmp_path / "presets"
    _write_preset(presets / "a.toml", preset_id="same")
    _write_preset(presets / "b.toml", preset_id="same")

    with pytest.raises(AssemblyError, match="duplicate preset id: same"):
        load_presets(presets, MODULES_DIR)


def test_load_presets_rejects_duplicate_modules(tmp_path: Path) -> None:
    presets = tmp_path / "presets"
    _write_preset(presets / "duplicate.toml", modules=("documents", "documents"))

    with pytest.raises(AssemblyError, match="duplicate module in preset: documents"):
        load_presets(presets, MODULES_DIR)


def test_load_presets_reuses_unknown_module_validation(tmp_path: Path) -> None:
    modules = tmp_path / "modules"
    presets = tmp_path / "presets"
    _module(modules / "available", "available")
    _write_preset(presets / "unknown-module.toml", modules=("missing",))

    with pytest.raises(AssemblyError, match=r"unknown module\(s\): missing"):
        load_presets(presets, modules)


@pytest.mark.parametrize(
    ("requires", "extra_modules", "message"),
    (
        (("missing",), (), "module root requires unknown module missing"),
        (("other",), (("other", ("root",)),), "dependency cycle involving root"),
    ),
)
def test_load_presets_reuses_dependency_validation(
    tmp_path: Path,
    requires: tuple[str, ...],
    extra_modules: tuple[tuple[str, tuple[str, ...]], ...],
    message: str,
) -> None:
    modules = tmp_path / "modules"
    presets = tmp_path / "presets"
    _module(modules / "root", "root", requires=requires)
    for module_id, dependencies in extra_modules:
        _module(modules / module_id, module_id, requires=dependencies)
    _write_preset(presets / "invalid-graph.toml", modules=("root",))

    with pytest.raises(AssemblyError, match=message):
        load_presets(presets, modules)


def test_load_presets_reuses_conflict_validation(tmp_path: Path) -> None:
    modules = tmp_path / "modules"
    presets = tmp_path / "presets"
    _module(modules / "safe", "safe", conflicts=("unsafe",))
    _module(modules / "unsafe", "unsafe")
    _write_preset(presets / "conflict.toml", modules=("safe", "unsafe"))

    with pytest.raises(AssemblyError, match="module conflict"):
        load_presets(presets, modules)


@pytest.mark.parametrize(
    ("modules", "adapters", "message"),
    (
        (("root",), {"other": "fake"}, "adapter selected for unselected module: other"),
        (("root",), {"root": "fake"}, "module root has no adapters"),
        (("root",), {"root": "missing"}, "unknown adapter for module root: missing"),
    ),
)
def test_load_presets_reuses_adapter_validation(
    tmp_path: Path,
    modules: tuple[str, ...],
    adapters: dict[str, str],
    message: str,
) -> None:
    modules_dir = tmp_path / "modules"
    presets = tmp_path / "presets"
    _module(modules_dir / "root", "root")
    if adapters.get("root") == "missing":
        _module_with_adapters(modules_dir / "root", "root")
    _write_preset(presets / "invalid-adapter.toml", modules=modules, adapters=adapters)

    with pytest.raises(AssemblyError, match=message):
        load_presets(presets, modules_dir)


def test_preset_modules_and_additions_are_deduplicated_before_dependency_closure(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "merged-closure"
    selected = assemble_project(
        destination,
        ("retrieval", "documents", "embeddings"),
        preset="rag-local",
    )

    assert selected == ("documents", "retrieval", "embeddings")
    _assert_generated_project_is_closed(destination)


def test_user_adapter_overrides_preset_adapter(tmp_path: Path) -> None:
    destination = tmp_path / "preset-adapter-override"
    selected = assemble_project(
        destination,
        preset="rag-local",
        adapters={"embeddings": "openai-compatible"},
    )

    assert selected == ("documents", "retrieval", "embeddings")
    package_root, _ = _assert_generated_project_is_closed(destination)
    assert (package_root / "adapters/openai_compatible_embeddings/provider.py").is_file()
    assert not (package_root / "adapters/fake/embeddings.py").exists()


def test_user_adapter_can_select_an_adapter_for_a_new_module(tmp_path: Path) -> None:
    destination = tmp_path / "preset-add-adapter"
    selected = assemble_project(
        destination,
        ("llm-text",),
        preset="minimal",
        adapters={"llm-text": "fake"},
    )

    assert selected == ("llm-text",)
    package_root, _ = _assert_generated_project_is_closed(destination)
    assert (package_root / "adapters/fake/text_generator.py").is_file()


def test_invalid_preset_adapter_override_fails_before_destination_creation(tmp_path: Path) -> None:
    destination = tmp_path / "invalid-preset-override"
    with pytest.raises(AssemblyError, match="unknown adapter for module llm-text: missing"):
        assemble_project(
            destination,
            preset="text-cli",
            adapters={"llm-text": "missing"},
        )
    assert not destination.exists()


def test_invalid_preset_fails_before_destination_creation(tmp_path: Path) -> None:
    presets = tmp_path / "presets"
    presets.mkdir()
    (presets / "broken.toml").write_text(
        'id = "broken"\ndescription = "Broken"\nmodules = [\n',
        encoding="utf-8",
    )
    destination = tmp_path / "invalid-preset"

    with pytest.raises(AssemblyError, match="invalid preset description"):
        assemble_project(
            destination,
            preset="broken",
            presets_dir=presets,
            modules_dir=MODULES_DIR,
        )
    assert not destination.exists()


def test_invalid_module_graph_fails_before_destination_creation(tmp_path: Path) -> None:
    modules = tmp_path / "modules"
    presets = tmp_path / "presets"
    _module(modules / "root", "root", requires=("missing",))
    _write_preset(presets / "broken-module.toml", modules=("root",))
    destination = tmp_path / "invalid-module"

    with pytest.raises(AssemblyError, match="requires unknown module"):
        assemble_project(
            destination,
            preset="broken-module",
            presets_dir=presets,
            modules_dir=modules,
        )
    assert not destination.exists()


def test_missing_assembly_source_fails_before_destination_creation(tmp_path: Path) -> None:
    modules = tmp_path / "modules"
    presets = tmp_path / "presets"
    _module_with_adapters(
        modules / "broken-source",
        "broken-source",
        adapters=(),
        files=("features/does-not-exist",),
    )
    (modules / "broken-source" / "module.toml").write_text(
        (modules / "broken-source" / "module.toml")
        .read_text(encoding="utf-8")
        .replace('default_adapter = "fake"\n', ""),
        encoding="utf-8",
    )
    _write_preset(
        presets / "broken-source.toml",
        preset_id="broken-source",
        modules=("broken-source",),
    )
    destination = tmp_path / "missing-source"

    with pytest.raises(AssemblyError, match="assembly file does not exist"):
        assemble_project(
            destination,
            preset="broken-source",
            presets_dir=presets,
            modules_dir=modules,
        )
    assert not destination.exists()


def test_create_ai_app_lists_validated_presets_without_a_destination() -> None:
    result = _run_create_ai_app("--list-presets")

    assert result.returncode == 0, result.stderr
    lines = result.stdout.strip().splitlines()
    assert [line.split(":", 1)[0] for line in lines] == [
        "artifact-pipeline",
        "minimal",
        "rag-local",
        "retrieval",
        "text-cli",
    ]
    assert lines[1] == "minimal: Foundation and core CLI only"
    assert lines[2] == (
        "rag-local: Local document retrieval with filesystem documents and fake embeddings"
    )


@pytest.mark.parametrize("combination", ("destination", "preset", "add", "adapter"))
def test_create_ai_app_list_presets_rejects_assembly_options(
    tmp_path: Path, combination: str
) -> None:
    destination = tmp_path / f"list-with-{combination}"
    arguments = ["--list-presets"]
    if combination == "destination":
        arguments.insert(0, str(destination))
    elif combination == "preset":
        arguments.extend(("--preset", "minimal"))
    elif combination == "add":
        arguments.extend(("--add", "llm-text"))
    else:
        arguments.extend(("--adapter", "llm-text=fake"))

    result = _run_create_ai_app(*arguments)

    assert result.returncode == 2
    assert "--list-presets" in result.stderr
    assert not destination.exists()


def test_create_ai_app_requires_destination_without_list_presets() -> None:
    result = _run_create_ai_app()

    assert result.returncode == 2
    assert "destination is required unless --list-presets is used" in result.stderr


def test_create_ai_app_rejects_unknown_preset_before_creating_destination(tmp_path: Path) -> None:
    destination = tmp_path / "unknown-preset-cli"
    result = _run_create_ai_app(str(destination), "--preset", "missing")

    assert result.returncode == 2
    assert "unknown preset: missing" in result.stderr
    assert not destination.exists()


def test_create_ai_app_reports_merged_preset_modules_and_adapters(tmp_path: Path) -> None:
    destination = tmp_path / "phase7-cli-preset"
    result = _run_create_ai_app(
        str(destination),
        "--preset",
        "rag-local",
        "--add",
        "llm-text",
        "--adapter",
        "embeddings=openai-compatible",
        "--adapter",
        "llm-text=fake",
    )

    assert result.returncode == 0, result.stderr
    assert "preset: rag-local" in result.stdout
    assert "modules: documents, retrieval, embeddings, llm-text" in result.stdout
    assert (
        "adapters: documents=filesystem, embeddings=openai-compatible, llm-text=fake"
        in result.stdout
    )
    assert destination.exists()


@pytest.mark.parametrize(
    ("preset", "expected_modules"),
    (
        ("minimal", ()),
        ("text-cli", ("llm-text",)),
        ("rag-local", ("documents", "retrieval", "embeddings")),
        ("artifact-pipeline", ("artifacts", "pipeline", "sqlite-artifacts")),
    ),
)
def test_formal_presets_generate_closed_linted_projects_with_offline_smoke_tests(
    tmp_path: Path,
    preset: str,
    expected_modules: tuple[str, ...],
) -> None:
    destination = tmp_path / f"formal-{preset}"
    selected = assemble_project(destination, preset=preset)

    assert selected == expected_modules
    _assert_generated_project_is_closed(destination)
    _assert_generated_project_lints(destination)
    _assert_generated_smoke_is_offline(destination)
    _run_generated_smoke(destination)


def test_formal_minimal_preset_contains_only_foundation_and_core_cli(tmp_path: Path) -> None:
    destination = tmp_path / "formal-minimal-foundation"
    assemble_project(destination, preset="minimal")
    package_root, _ = _assert_generated_project_is_closed(destination)

    assert (package_root / "foundation").is_dir()
    assert (package_root / "interfaces/cli/core.py").is_file()
    assert not (package_root / "features").exists()
    assert not (package_root / "adapters").exists()
    assert not (package_root / "contracts").exists()
    project = tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))
    assert "httpx" not in "\n".join(project["project"]["dependencies"])


def test_formal_text_cli_preset_uses_fake_ask_without_httpx(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "formal-text-cli-behavior"
    assemble_project(destination, preset="text-cli")
    package_root, package = _assert_generated_project_is_closed(destination)

    assert (package_root / "adapters/fake/text_generator.py").is_file()
    assert not (package_root / "adapters/openai_compatible").exists()
    project = tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))
    assert "httpx" not in "\n".join(project["project"]["dependencies"])
    assert "AI_LLM_API_KEY" not in (destination / ".env.example").read_text(encoding="utf-8")

    monkeypatch.syspath_prepend(str(destination / "src"))
    importlib.invalidate_caches()
    app_module = importlib.import_module(f"{package}.interfaces.cli.app")
    result = CliRunner().invoke(app_module.app, ["ask", "hello"])

    assert result.exit_code == 0, result.stdout
    assert result.stdout.strip() == "Fake provider response"


def test_formal_rag_local_preset_searches_locally_with_fake_embeddings(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "formal-rag-local-behavior"
    assemble_project(destination, preset="rag-local")
    package_root, package = _assert_generated_project_is_closed(destination)

    assert (package_root / "adapters/filesystem").is_dir()
    assert (package_root / "adapters/fake/embeddings.py").is_file()
    assert not (package_root / "adapters/openai_compatible_embeddings").exists()
    project = tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))
    assert "httpx" not in "\n".join(project["project"]["dependencies"])
    monkeypatch.syspath_prepend(str(destination / "src"))
    importlib.invalidate_caches()
    settings_module = importlib.import_module(
        f"{package}.features.embeddings.settings"
    )
    assert settings_module.load_embedding_settings().enabled is False

    document = tmp_path / "notes.txt"
    document.write_text("offline fake embedding needle", encoding="utf-8")
    app_module = importlib.import_module(f"{package}.interfaces.cli.app")
    result = CliRunner().invoke(
        app_module.app,
        ["search", str(document), "needle"],
        env={"AI_EMBEDDING_ENABLED": "true"},
    )

    assert result.exit_code == 0, result.stdout
    assert "offline fake embedding needle" in result.stdout


def test_formal_artifact_pipeline_preset_contains_only_local_artifact_capabilities(
    tmp_path: Path,
) -> None:
    destination = tmp_path / "artifact-pipeline-check"
    assemble_project(destination, preset="artifact-pipeline")
    package_root, _ = _assert_generated_project_is_closed(destination)

    assert (package_root / "features/artifacts").is_dir()
    assert (package_root / "features/pipeline").is_dir()
    assert (package_root / "adapters/sqlite_artifacts").is_dir()
    assert not (package_root / "features/text_generation").exists()
    assert not (package_root / "features/embeddings").exists()
    assert not (package_root / "adapters/openai_compatible").exists()
    assert not (package_root / "adapters/openai_compatible_embeddings").exists()

    project = tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = "\n".join(project["project"]["dependencies"])
    assert "httpx" not in dependencies
    smoke = _assert_generated_smoke_is_offline(destination)
    assert "test_version" in smoke
    assert "test_check" in smoke
    assert "test_local_search" not in smoke
    assert "test_fake_ask" not in smoke


def test_rag_local_openai_embedding_override_is_disabled_by_default_and_offline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    destination = tmp_path / "rag-remote-embedding"
    assemble_project(
        destination,
        preset="rag-local",
        adapters={"embeddings": "openai-compatible"},
    )
    package_root, package = _assert_generated_project_is_closed(destination)

    assert (package_root / "adapters/openai_compatible_embeddings/provider.py").is_file()
    assert not (package_root / "adapters/fake/embeddings.py").exists()
    assert not (package_root / "adapters/fake/text_generator.py").exists()
    assert not (package_root / "adapters/openai_compatible").exists()
    project = tomllib.loads((destination / "pyproject.toml").read_text(encoding="utf-8"))
    assert project["project"]["dependencies"] == [
        "httpx>=0.27,<1",
        "pydantic-settings>=2.0,<3",
        "typer>=0.12,<1",
    ]
    env_example = (destination / ".env.example").read_text(encoding="utf-8")
    assert "AI_EMBEDDING_ENABLED=false" in env_example
    assert "AI_EMBEDDING_API_KEY=" in env_example
    assert "AI_EMBEDDING_BASE_URL=https://api.openai.com/v1" in env_example
    assert "AI_LLM_" not in env_example

    monkeypatch.syspath_prepend(str(destination / "src"))
    importlib.invalidate_caches()
    settings_module = importlib.import_module(
        f"{package}.features.embeddings.settings"
    )
    settings = settings_module.load_embedding_settings()
    assert settings.provider == "openai_compatible"
    assert settings.enabled is False

    document = tmp_path / "offline.txt"
    document.write_text("local keyword result", encoding="utf-8")
    app_module = importlib.import_module(f"{package}.interfaces.cli.app")
    result = CliRunner().invoke(app_module.app, ["search", str(document), "keyword"])

    assert result.exit_code == 0, result.stdout
    assert "local keyword result" in result.stdout
