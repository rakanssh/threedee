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
- Dry-run mode

The repo has been initialized with git and has an initial commit.

## Known Gaps

- TRELLIS.2 still needs to be installed and wrapped per target machine.
- SkinTokens is not installed or wrapped yet.
- Blender cleanup script is not implemented yet.
- glTF validation command is configurable but not installed/wired.
- No automated unit tests yet; smoke checks are command-based.

## Next Likely Work

1. Install the CLI editable on the target machine.
2. Configure OpenRouter through `threedee config set-openrouter`.
3. Test `--until spec` and `--until image`.
4. Install TRELLIS.2 outside this repo and get image-to-GLB inference working manually.
5. Wrap the working TRELLIS command in ignored local config.
6. Install SkinTokens and get rigging working manually.
7. Wrap the working SkinTokens command in ignored local config.
8. Add a Blender cleanup/preview script once raw meshes are being generated.
