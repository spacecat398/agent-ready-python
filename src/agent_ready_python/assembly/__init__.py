"""Static project assembly utilities."""

from agent_ready_python.assembly.models import (
    AdapterSelection,
    AdapterSelectionInput,
    AdapterSpec,
    AssemblyError,
    AssemblyPlan,
    ModuleSpec,
    PresetSpec,
    normalize_adapter_selections,
    parse_adapter_selection,
    parse_adapter_selections,
)
from agent_ready_python.assembly.service import (
    assemble_project,
    list_presets,
    load_presets,
    resolve_adapters,
    resolve_assembly,
    resolve_modules,
    resolve_preset,
)

__all__ = [
    "AdapterSelection",
    "AdapterSelectionInput",
    "AdapterSpec",
    "AssemblyPlan",
    "AssemblyError",
    "ModuleSpec",
    "PresetSpec",
    "assemble_project",
    "list_presets",
    "load_presets",
    "normalize_adapter_selections",
    "parse_adapter_selection",
    "parse_adapter_selections",
    "resolve_assembly",
    "resolve_adapters",
    "resolve_modules",
    "resolve_preset",
]
