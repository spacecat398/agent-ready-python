import ast
import tomllib
from pathlib import Path

import agent_ready_python

PROJECT_ROOT = Path(__file__).parents[1]
PACKAGE_ROOT = Path(agent_ready_python.__file__).resolve().parent
CATALOG_ROOT = PACKAGE_ROOT / "catalog"
MODULES_DIR = CATALOG_ROOT / "modules"
PRESETS_DIR = CATALOG_ROOT / "presets"


def absolute_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            imports.add(node.module)
    return imports


def test_foundation_does_not_depend_on_optional_layers() -> None:
    forbidden = (
        "agent_ready_python.features",
        "agent_ready_python.adapters",
        "agent_ready_python.interfaces",
    )
    for path in (PACKAGE_ROOT / "foundation").glob("*.py"):
        assert not any(
            imported.startswith(forbidden)
            for imported in absolute_imports(path)
        ), path


def test_core_cli_does_not_import_text_generation() -> None:
    imports = absolute_imports(PACKAGE_ROOT / "interfaces" / "cli" / "core.py")

    assert not any("text_generation" in imported for imported in imports)
    assert "agent_ready_python.bootstrap" not in imports


def test_catalog_is_package_owned_and_legacy_root_resources_are_absent() -> None:
    assert not (PROJECT_ROOT / "modules").exists()
    assert not (PROJECT_ROOT / "presets").exists()
    assert MODULES_DIR.is_dir()
    assert PRESETS_DIR.is_dir()


def test_module_descriptors_are_complete_and_reference_existing_package_sources() -> None:
    required_fields = {
        "id",
        "kind",
        "description",
        "requires",
        "optional",
        "conflicts",
        "python_dependencies",
        "exports",
        "files",
    }
    descriptor_paths = sorted(MODULES_DIR.glob("*/module.toml"))
    assert descriptor_paths

    for path in descriptor_paths:
        with path.open("rb") as file:
            descriptor = tomllib.load(file)

        assert required_fields <= descriptor.keys(), path
        assert descriptor["id"] == path.parent.name
        assert descriptor["description"].strip()
        assert all((PACKAGE_ROOT / relative).exists() for relative in descriptor["files"]), path

        adapters = descriptor.get("adapters", [])
        assert len({adapter["id"] for adapter in adapters}) == len(adapters)
        for adapter in adapters:
            assert {"id", "python_dependencies", "files"} <= adapter.keys()
            assert adapter["id"].strip()
            assert all((PACKAGE_ROOT / relative).exists() for relative in adapter["files"]), path


def test_preset_descriptors_are_complete_and_owned_by_the_package_catalog() -> None:
    required_fields = {"id", "description", "modules", "adapters"}
    descriptor_paths = sorted(PRESETS_DIR.glob("*.toml"))
    assert descriptor_paths

    for path in descriptor_paths:
        with path.open("rb") as file:
            descriptor = tomllib.load(file)

        assert required_fields <= descriptor.keys(), path
        assert descriptor["id"] == path.stem
        assert descriptor["description"].strip()
        assert all(isinstance(module, str) and module.strip() for module in descriptor["modules"])
        assert isinstance(descriptor["adapters"], dict)


def test_module_descriptors_have_no_missing_dependencies() -> None:
    descriptors = []
    for path in MODULES_DIR.glob("*/module.toml"):
        with path.open("rb") as file:
            descriptors.append(tomllib.load(file))

    module_ids = {descriptor["id"] for descriptor in descriptors}
    assert module_ids
    for descriptor in descriptors:
        assert set(descriptor.get("requires", [])) <= module_ids


def test_module_descriptors_have_no_required_dependency_cycles() -> None:
    descriptors = {}
    for path in MODULES_DIR.glob("*/module.toml"):
        with path.open("rb") as file:
            descriptor = tomllib.load(file)
        descriptors[descriptor["id"]] = descriptor

    def visit(module_id: str, path: tuple[str, ...]) -> None:
        assert module_id not in path, f"module dependency cycle: {path + (module_id,)}"
        for dependency in descriptors[module_id].get("requires", []):
            visit(dependency, path + (module_id,))

    for module_id in descriptors:
        visit(module_id, ())


def test_keyword_retrieval_public_api_does_not_import_embeddings() -> None:
    path = PACKAGE_ROOT / "features" / "retrieval" / "__init__.py"

    assert not any("embedding" in imported for imported in absolute_imports(path))


def test_pipeline_feature_does_not_import_sqlite_adapter() -> None:
    for path in (PACKAGE_ROOT / "features" / "pipeline").glob("*.py"):
        assert not any(
            imported.startswith("agent_ready_python.adapters.sqlite_artifacts")
            for imported in absolute_imports(path)
        ), path
