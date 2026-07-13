"""Models and errors for the offline assembler."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType


class AssemblyError(ValueError):
    """Raised when a module selection or destination is unsafe or invalid."""


@dataclass(frozen=True, slots=True)
class AdapterSelection:
    """A single explicit module-to-Adapter choice."""

    module: str
    adapter: str

    def __post_init__(self) -> None:
        if not isinstance(self.module, str) or not self.module.strip():
            raise AssemblyError("adapter selection module must not be empty")
        if not isinstance(self.adapter, str) or not self.adapter.strip():
            raise AssemblyError("adapter selection adapter must not be empty")
        object.__setattr__(self, "module", self.module.strip())
        object.__setattr__(self, "adapter", self.adapter.strip())


AdapterSelectionInput = Mapping[str, str] | Iterable[AdapterSelection]


def parse_adapter_selection(value: str) -> AdapterSelection:
    """Parse one ``MODULE=ADAPTER`` command-line value."""

    if not isinstance(value, str) or value.count("=") != 1:
        raise AssemblyError("adapter must use MODULE=ADAPTER format")
    module, adapter = (part.strip() for part in value.split("=", 1))
    if not module or not adapter:
        raise AssemblyError("adapter must use MODULE=ADAPTER format")
    return AdapterSelection(module=module, adapter=adapter)


def parse_adapter_selections(values: Iterable[str]) -> tuple[AdapterSelection, ...]:
    """Parse repeated command-line values and reject duplicate module assignments."""

    if values is None:
        raise AssemblyError("adapter selections must be an iterable of MODULE=ADAPTER values")
    try:
        iterator = iter(values)
    except TypeError as exc:
        message = "adapter selections must be an iterable of MODULE=ADAPTER values"
        raise AssemblyError(message) from exc

    result: list[AdapterSelection] = []
    seen_modules: set[str] = set()
    for value in iterator:
        selection = parse_adapter_selection(value)
        if selection.module in seen_modules:
            raise AssemblyError(
                f"duplicate adapter selection for module: {selection.module}"
            )
        seen_modules.add(selection.module)
        result.append(selection)
    return tuple(result)


def normalize_adapter_selections(
    selections: AdapterSelectionInput | None,
) -> tuple[AdapterSelection, ...]:
    """Normalize the structured API form while preserving duplicate validation."""

    if selections is None:
        return ()
    if isinstance(selections, Mapping):
        values = (AdapterSelection(module, adapter) for module, adapter in selections.items())
    else:
        values = selections

    result: list[AdapterSelection] = []
    seen_modules: set[str] = set()
    try:
        iterator = iter(values)
    except TypeError as exc:
        message = "adapter selections must be a mapping or AdapterSelection iterable"
        raise AssemblyError(message) from exc
    for value in iterator:
        if not isinstance(value, AdapterSelection):
            raise AssemblyError("adapter selections must contain AdapterSelection values")
        if value.module in seen_modules:
            raise AssemblyError(f"duplicate adapter selection for module: {value.module}")
        seen_modules.add(value.module)
        result.append(value)
    return tuple(result)


@dataclass(frozen=True, slots=True)
class AdapterSpec:
    """Static metadata for one selectable Adapter implementation."""

    id: str
    python_dependencies: tuple[str, ...]
    files: tuple[str, ...]
    env_example: tuple[str, ...]


@dataclass(frozen=True)
class ModuleSpec:
    id: str
    kind: str
    requires: tuple[str, ...]
    optional: tuple[str, ...]
    conflicts: tuple[str, ...]
    python_dependencies: tuple[str, ...]
    files: tuple[str, ...]
    env_example: tuple[str, ...]
    adapters: tuple[AdapterSpec, ...]
    source: Path
    default_adapter: str | None = None


@dataclass(frozen=True, slots=True)
class AssemblyPlan:
    """Validated modules and Adapters for one generated project."""

    modules: tuple[ModuleSpec, ...]
    adapters: Mapping[str, AdapterSpec]

    def __post_init__(self) -> None:
        object.__setattr__(self, "adapters", MappingProxyType(dict(self.adapters)))


@dataclass(frozen=True, slots=True)
class PresetSpec:
    """Static metadata for one declarative project composition."""

    id: str
    description: str
    modules: tuple[str, ...]
    adapters: Mapping[str, str]
    source: Path

    def __post_init__(self) -> None:
        if not isinstance(self.id, str) or not self.id.strip():
            raise AssemblyError("preset id must not be empty")
        if not isinstance(self.description, str) or not self.description.strip():
            raise AssemblyError("preset description must not be empty")
        if not isinstance(self.modules, (tuple, list)):
            raise AssemblyError("preset modules must be a tuple of strings")

        modules: list[str] = []
        seen_modules: set[str] = set()
        for module in self.modules:
            if not isinstance(module, str) or not module.strip():
                raise AssemblyError("preset modules must contain non-empty strings")
            module = module.strip()
            if module in seen_modules:
                raise AssemblyError(f"duplicate module in preset: {module}")
            seen_modules.add(module)
            modules.append(module)

        if not isinstance(self.adapters, Mapping):
            raise AssemblyError("preset adapters must be a mapping of module to adapter")
        adapters: dict[str, str] = {}
        for module, adapter in self.adapters.items():
            if not isinstance(module, str) or not module.strip():
                raise AssemblyError("preset adapter module must not be empty")
            if not isinstance(adapter, str) or not adapter.strip():
                raise AssemblyError("preset adapter must not be empty")
            module = module.strip()
            adapter = adapter.strip()
            if module in adapters:
                raise AssemblyError(f"duplicate adapter module in preset: {module}")
            adapters[module] = adapter

        object.__setattr__(self, "id", self.id.strip())
        object.__setattr__(self, "description", self.description.strip())
        object.__setattr__(self, "modules", tuple(modules))
        object.__setattr__(self, "adapters", MappingProxyType(dict(sorted(adapters.items()))))
