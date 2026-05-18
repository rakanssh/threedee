# threedee

Prompt-to-rigged-3D asset pipeline.

The CLI owns orchestration and artifacts. OpenRouter handles prompt expansion and reference image generation. Local model commands handle 3D mesh generation and rigging on the target GPU machine.

## Install

### Agent-Assisted Setup

This package includes agent-facing setup instructions in `AGENTS.md` and `.agents/`. You can ask a local coding agent to use them to help install the CLI, configure OpenRouter, and wire GPU backends such as TRELLIS.2 or SkinTokens.

This path is experimental: backend setup may install system packages, GPU runtimes, model repositories, and large checkpoints. Review the commands your agent proposes before approving them, and keep secrets, checkpoints, generated runs, and virtual environments out of git.

Before running GPU backends, check whether the selected model repositories require accepted licenses or gated access. Some mesh backends depend on multiple Hugging Face models, not just the main backend checkpoint. Authenticate in the same environment and OS user that will run the backend command.

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Configure

Inspect the effective config:

```bash
threedee config show
```

Set OpenRouter model names and keys in `threedee.local.toml`, which is ignored by git:

```bash
threedee config set-openrouter --llm-model google/gemini-3-flash-preview
threedee config set-openrouter --image-model openai/gpt-5.4-image-2
threedee config set-openrouter --shared-api-key "..."
```

If needed, set separate completion endpoints:

```bash
threedee config set-openrouter --llm-url https://openrouter.ai/api/v1/chat/completions
threedee config set-openrouter --image-url https://openrouter.ai/api/v1/chat/completions
```

You can also use environment variables instead of local config secrets:

```bash
export OPENROUTER_API_KEY="..."
```

PowerShell:

```powershell
$env:OPENROUTER_API_KEY = "..."
```

The image key falls back to the LLM key unless you set a separate image key:

```bash
threedee config set-openrouter --image-api-key "..."
```

Edit `threedee.toml` on the target GPU machine and fill in the local stage commands for TRELLIS.2 and SkinTokens. Each command gets formatted with:

- `{input}`: input image or mesh path
- `{output}`: expected output path
- `{run_dir}`: current run directory
- `{prompt}`: original user prompt
- `{seed}`: seed, if provided

Quote placeholders in commands because run paths can contain spaces on Windows.

For local GPU backends, prefer an ignored `threedee.local.toml` command that calls a small wrapper script. The wrapper should pin or document the exact upstream model IDs it uses, stream progress and download logs to stdout/stderr, and write the expected `{output}` artifact. First runs may download many gigabytes and may use substantial CPU RAM while checkpoints are assembled before GPU execution begins.

## Commands

Smoke test without API or model calls:

```bash
threedee generate "stylized armored knight" --dry-run
threedee status
threedee list
```

Generate only the OpenRouter spec and reference image:

```bash
threedee generate "stylized armored knight with oversized gauntlets" --until image
```

Generate end to end once local model commands are configured:

```bash
threedee generate "stylized armored knight with oversized gauntlets" --seed 12345
```

Use an existing reference image:

```bash
threedee generate "stylized armored knight" --image path/to/reference.png
```

Benchmark alternates on an existing run:

```bash
threedee benchmark mesh hunyuan3d <job_id>
threedee benchmark rig riganything <job_id>
```

Open the latest run folder:

```bash
threedee open
```

## Run Outputs

Each run writes to `runs/<job_id>/`:

- `manifest.json`: status, stage metadata, artifact paths, errors
- `asset_spec.json`: structured prompt spec from the LLM
- `reference.png`: generated or supplied reference image
- `asset_raw.glb`: local mesh model output
- `asset_clean.glb`: cleanup output, or copied raw mesh if cleanup is not configured
- `asset_rigged.glb`: local rigging model output
- `*.log`: stdout/stderr for configured local commands

## Current Pipeline Defaults

- LLM: `openrouter:google/gemini-3-flash-preview`
- Image: `openrouter:openai/gpt-5.4-image-2`
- Mesh: local `trellis2`
- Rig: local `skintokens`

Use `threedee.toml` to wire the target GPU environment after local model commands are working manually.
