# Handoff

## Current State

The repo has a working dependency-light Python CLI scaffold.

Implemented:

- `init`
- `generate`
- `status`
- `list`
- `open`
- `benchmark`
- OpenRouter LLM/image client
- `config show`
- `config set-openrouter`
- Layered local config through ignored `threedee.local.toml`
- JSON run manifests
- Config-driven local stage commands
- Local stage output streaming to the console and per-run logs
- Dry-run mode

The repo has been initialized with git and has an initial commit.

## Known Gaps

- Blender cleanup script is not implemented yet.
- glTF validation command is configurable but not installed/wired.
- No automated unit tests yet; smoke checks are command-based.

TRELLIS.2 and SkinTokens have been proven locally on one target machine through ignored wrapper scripts and local config. Do not treat those wrapper paths as portable repo defaults; use `.agents/setup.md` to reproduce the pattern on another machine.

## Next Likely Work

1. Install the CLI editable on the target machine.
2. Configure OpenRouter through `threedee config set-openrouter`.
3. Test `--until spec` and `--until image`.
4. Install and wire TRELLIS.2 outside this repo if the target machine does not already have it.
5. Install and wire SkinTokens outside this repo if the target machine does not already have it.
6. Add a Blender cleanup/preview script once raw meshes are being generated.
