# Instructions for coding agents

1. Read `PROGRESS.md` and the modular architecture design before changing code.
2. Prefer `uv` and run `uv sync` before verification.
3. Never overwrite an existing `.env`.
4. Never print, store, or commit API keys.
5. Do not call a remote provider unless the user explicitly asks for a live request.
6. Keep optional features independent from Foundation and core CLI commands.
7. Use explicit construction in `bootstrap.py`; do not add automatic module discovery.
8. Run `uv run ruff check .` and `uv run pytest` before claiming success.
9. Update `PROGRESS.md` with a timestamp when substantive work starts or finishes.
