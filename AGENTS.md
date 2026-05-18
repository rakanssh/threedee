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
- Preserve cross-platform behavior. Runtime targets may be Windows or Linux GPU workstations.
- Prefer config-driven local commands over hardcoded model repo paths.
- Keep stage outputs manifest-driven and inspectable.
- Keep the project focused on local orchestration and reproducible asset generation workflows.
- Treat heavy model installs as local environment setup, not repo implementation. Install external repos/checkpoints outside this repository and wire them through ignored local config.

## Environment Setup Guidance

When helping a user set up a GPU machine:

- First verify the CLI itself with dry-run commands before touching model installs.
- Inspect available tools and GPU/runtime support yourself before asking setup questions.
- Ask where the user wants large model repos, checkpoints, and caches installed only when no obvious local convention exists.
- Ask how the user wants to store OpenRouter secrets. Prefer `threedee config set-openrouter --shared-api-key ...`, which writes to ignored `threedee.local.toml`; environment variables are also acceptable.
- Keep `threedee.toml` as shared defaults. Put machine-specific commands, paths, endpoints, model names, and secrets in ignored local config.
- Install and test each heavy backend manually before wiring it into `threedee`. A stage command is ready only when it can take the documented placeholders and create the expected artifact path.
- Before first inference, identify all gated or license-restricted model repositories used by a backend and ask the user to request/accept access where needed. Authenticate in the same environment and user account that will execute the backend command.
- Prefer explicit model IDs, revisions, or locally documented versions for upstream checkpoints. If a backend's dependencies are known to be sensitive to library versions, record the tested model IDs and relevant package versions in agent notes.
- Expect first backend runs to download large checkpoints and to use CPU RAM while loading or assembling models before work moves to the GPU. Make wrappers stream progress/download logs to stdout/stderr so `threedee` can surface them while also writing stage logs.
- For image-to-3D mesh generation, guide reference image prompts toward one isolated subject in one view. Avoid character sheets, turnarounds, split-screen views, text, or duplicate subjects unless the selected backend explicitly supports multi-view input.
- Record reusable setup findings in `.agents/handoff.md` or `.agents/setup.md`, but do not record API keys, checkpoint tokens, or private paths that should remain local.

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
- `.agents/setup.md`: environment setup playbook for future agents.

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
