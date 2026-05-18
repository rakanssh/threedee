# threedee

Prompt-to-rigged-3D asset pipeline.

The CLI owns orchestration and artifacts. OpenRouter handles prompt expansion and reference image generation. Local model commands handle 3D mesh generation and rigging on the target GPU machine.

## Install

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

Set your OpenRouter key:

```bash
export OPENROUTER_API_KEY="..."
```

PowerShell:

```powershell
$env:OPENROUTER_API_KEY = "..."
```

Edit `threedee.toml` on the target GPU machine and fill in the local stage commands for TRELLIS.2 and SkinTokens. Each command gets formatted with:

- `{input}`: input image or mesh path
- `{output}`: expected output path
- `{run_dir}`: current run directory
- `{prompt}`: original user prompt
- `{seed}`: seed, if provided

Quote placeholders in commands because run paths can contain spaces on Windows.

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
