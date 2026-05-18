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
- JSON run manifests
- Config-driven local stage commands
- Dry-run mode

The repo has been initialized with git and has an initial commit.

## Known Gaps

- TRELLIS.2 is not installed or wrapped yet.
- SkinTokens is not installed or wrapped yet.
- Blender cleanup script is not implemented yet.
- glTF validation command is configurable but not installed/wired.
- No automated unit tests yet; smoke checks are command-based.

## Next Likely Work

1. Move the repo to the target GPU workstation.
2. Install the CLI editable.
3. Install TRELLIS.2 and get its demo inference working manually.
4. Wrap the working TRELLIS command in `threedee.toml`.
5. Install SkinTokens and get rigging working manually.
6. Wrap the working SkinTokens command in `threedee.toml`.
7. Add a Blender cleanup/preview script once raw meshes are being generated.
