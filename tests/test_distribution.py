import tomllib
from pathlib import Path

import agent_ready_python

PROJECT_ROOT = Path(__file__).parents[1]
WORKFLOW_PATH = PROJECT_ROOT / ".github" / "workflows" / "ci.yml"


def _project_metadata() -> dict[str, object]:
    with (PROJECT_ROOT / "pyproject.toml").open("rb") as file:
        return tomllib.load(file)


def test_distribution_configuration_keeps_package_catalog_and_tests_in_source_artifacts() -> None:
    metadata = _project_metadata()
    targets = metadata["tool"]["hatch"]["build"]["targets"]
    wheel = targets["wheel"]
    sdist = targets["sdist"]

    assert "src/agent_ready_python" in wheel["packages"]
    assert {
        "src/agent_ready_python/**",
        "tests/**",
        "README.md",
        "LICENSE",
        "CHANGELOG.md",
        "RELEASE_CHECKLIST.md",
        "modular-architecture-design.md",
        "agent-ready-python-design.md",
    } <= set(sdist["include"])


def test_project_metadata_matches_package_version_and_declares_public_entry_points() -> None:
    project = _project_metadata()["project"]

    assert project["version"] == agent_ready_python.__version__
    assert project["requires-python"] == ">=3.12"
    assert project["scripts"] == {
        "ai-app": "agent_ready_python.interfaces.cli.app:main",
        "create-ai-app": "agent_ready_python.assembly.cli:main",
    }


def test_project_metadata_declares_confirmed_license_author_and_repository() -> None:
    project = _project_metadata()["project"]

    assert project["license"] == "MIT"
    assert any(author["name"] == "spacecat398" for author in project["authors"])
    assert project["urls"]["Repository"] == "https://github.com/spacecat398/agent-ready-python"
    assert (PROJECT_ROOT / "LICENSE").read_text(encoding="utf-8").startswith("MIT License")


def test_project_metadata_contains_release_classifiers_and_keywords() -> None:
    project = _project_metadata()["project"]

    assert "code generator" in project["keywords"]
    assert {
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Development Status :: 4 - Beta",
        "Topic :: Software Development :: Code Generators",
    } <= set(project["classifiers"])


def test_distribution_configuration_excludes_local_environment_cache_and_build_outputs() -> None:
    excludes = set(_project_metadata()["tool"]["hatch"]["build"]["targets"]["sdist"]["exclude"])

    assert {
        "**/.env",
        "**/.env.*",
        "**/.venv/**",
        "**/.pytest_cache/**",
        "**/.ruff_cache/**",
        "**/__pycache__/**",
        "**/build/**",
        "**/dist/**",
    } <= excludes


def test_release_documents_keep_remaining_pending_confirmation_items() -> None:
    changelog_path = PROJECT_ROOT / "CHANGELOG.md"
    checklist_path = PROJECT_ROOT / "RELEASE_CHECKLIST.md"
    assert changelog_path.is_file()
    assert checklist_path.is_file()

    changelog_lines = changelog_path.read_text(encoding="utf-8").splitlines()
    assert "## [0.1.0] - 2026-07-13" in changelog_lines

    completed_items = [
        line.lower()
        for line in checklist_path.read_text(encoding="utf-8").splitlines()
        if line.lstrip().startswith("- [x]")
    ]
    pending_items = [
        line.lower()
        for line in checklist_path.read_text(encoding="utf-8").splitlines()
        if line.lstrip().startswith("- [ ]")
    ]
    assert any(
        "final version" in completed_item
        and "0.1.0" in completed_item
        and "v0.1.0" in completed_item
        for completed_item in completed_items
    )
    assert not any("final version" in pending_item for pending_item in pending_items)
    assert all(
        any(item in pending_item for pending_item in pending_items)
        for item in (
            "pypi project name",
            "trusted-publishing",
            "clean checkout",
            "api key",
        )
    )


def test_ci_workflow_describes_offline_wheel_smoke_without_publish_steps() -> None:
    assert WORKFLOW_PATH.is_file()
    workflow = WORKFLOW_PATH.read_text(encoding="utf-8")

    assert all(
        fragment in workflow
        for fragment in (
            "uv build",
            "uv pip install --python",
            '"$wheel"',
            "--list-presets",
            'uv run --directory "$validation_root/minimal" pytest',
            'uv run --directory "$validation_root/rag-local" pytest',
        )
    )
    lowered_workflow = workflow.lower()
    assert all(term not in lowered_workflow for term in ("publish", "upload", "token"))
