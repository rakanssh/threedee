# AGENTS.md

Guidance for coding agents working in this repository.

## Project

`threedee` is a prompt-to-rigged-3D asset pipeline CLI.

The CLI orchestrates:

```text
prompt
  -> OpenRouter LLM asset spec
  -> OpenRouter reference image
  -> local mesh generation command
  -> optional cleanup command
  -> local rigging command
  -> optional validation command
```

The heavy 3D model repositories and checkpoints are intentionally not vendored here. They should be installed in the target GPU environment and wired through `threedee.toml`.

## Development Rules

- Keep the CLI dependency-light unless a dependency clearly pays for itself.
- Do not commit generated `runs/` artifacts, API keys, checkpoints, model repos, or virtualenvs.
- Preserve cross-platform behavior. This repo is developed on macOS, but the runtime target is Windows with an NVIDIA RTX 5090.
- Prefer config-driven local commands over hardcoded model repo paths.
- Keep stage outputs manifest-driven and inspectable.
- Keep the project focused on local orchestration and reproducible asset generation workflows.

## Common Commands

```bash
python3 -m compileall threedee
python3 -m threedee.cli --help
python3 -m threedee.cli generate "stylized armored knight" --dry-run
python3 -m threedee.cli status
python3 -m threedee.cli list
```

After installing editable:

```bash
python -m pip install -e .
threedee generate "stylized armored knight" --dry-run
```

## Important Files

- `README.md`: setup and CLI usage.
- `threedee.toml`: default local pipeline config.
- `threedee/cli.py`: argparse command surface.
- `threedee/pipeline.py`: orchestration and local command execution.
- `threedee/openrouter.py`: OpenRouter LLM/image client.
- `threedee/manifest.py`: run manifest helpers.
- `.agents/`: agent-facing project notes.

## Current Defaults

- LLM: `openrouter:google/gemini-3-flash-preview`
- Image: `openrouter:openai/gpt-5.4-image-2`
- Primary mesh backend: `trellis2`
- Benchmark mesh backend: `hunyuan3d`
- Primary rig backend: `skintokens`
- Benchmark rig backend: `riganything`

## Before Finishing Changes

Run at least:

```bash
python3 -m compileall threedee
python3 -m threedee.cli generate "smoke test asset" --dry-run
python3 -m threedee.cli status
```

Clean generated `runs/` before committing unless sample artifacts are intentionally part of the change.
