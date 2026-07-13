"""The create-ai-app command."""

import argparse
from pathlib import Path

from agent_ready_python.assembly import (
    AssemblyError,
    assemble_project,
    list_presets,
    parse_adapter_selections,
    resolve_assembly,
)


def main() -> None:
    parser = argparse.ArgumentParser(prog="create-ai-app")
    parser.add_argument("destination", type=Path, nargs="?")
    parser.add_argument("--preset", default=None, help="Use a static preset by ID")
    parser.add_argument("--add", action="append", default=[])
    parser.add_argument(
        "--list-presets",
        action="store_true",
        help="List validated static presets and exit",
    )
    parser.add_argument(
        "--adapter",
        action="append",
        default=[],
        metavar="MODULE=ADAPTER",
        help="Select one Adapter for a module; may be repeated",
    )
    args = parser.parse_args()

    if args.list_presets:
        if args.destination is not None:
            parser.error("--list-presets does not accept a destination")
        if args.preset is not None or args.add or args.adapter:
            parser.error("--list-presets cannot be combined with assembly options")
        try:
            presets = list_presets()
        except AssemblyError as exc:
            parser.error(str(exc))
        for preset in presets:
            print(f"{preset.id}: {preset.description}")
        return

    if args.destination is None:
        parser.error("destination is required unless --list-presets is used")

    try:
        adapters = parse_adapter_selections(args.adapter)
        plan = resolve_assembly(tuple(args.add), preset=args.preset, adapters=adapters)
        selected = assemble_project(
            args.destination,
            assembly_plan=plan,
        )
    except AssemblyError as exc:
        parser.error(str(exc))

    module_summary = ", ".join(selected) or "foundation"
    adapter_summary = ", ".join(
        f"{module}={adapter.id}" for module, adapter in sorted(plan.adapters.items())
    ) or "none"
    preset_summary = f"; preset: {args.preset}" if args.preset is not None else ""
    print(
        f"Created {args.destination}{preset_summary}; modules: {module_summary}; "
        f"adapters: {adapter_summary}"
    )
