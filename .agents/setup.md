# Setup Playbook

Use this as a self-contained guide for helping a user install and configure [`rakanssh/threedee`](https://github.com/rakanssh/threedee) on a local GPU machine.

## Before You Begin

Before installing heavy backends, tell the user that setup can be a lengthy process. A full local GPU setup may take hours on a fresh machine and can involve many large downloads for model repositories, Python environments, CUDA/PyTorch packages, Hugging Face checkpoints, and caches. Depending on selected backends and cache reuse, plan for tens of gigabytes of disk usage, and roughly 75 GB or more is possible.

Ask the user to approve large downloads, third-party license or gated-model access, and credential storage before proceeding. Make clear that they should review commands before the agent runs them, especially commands that install system packages, modify shell profiles, or store tokens.

Ask the user to create or sign in to a Hugging Face account before backend setup. For the current TRELLIS.2 path, ask them to open these model pages, accept any licenses, and request access where gated:

- [microsoft/TRELLIS.2-4B](https://huggingface.co/microsoft/TRELLIS.2-4B)
- [briaai/RMBG-2.0](https://huggingface.co/briaai/RMBG-2.0)
- [facebook/dinov3-vitl16-pretrain-lvd1689m](https://huggingface.co/facebook/dinov3-vitl16-pretrain-lvd1689m)

The installing agent should still verify the backend's current model requirements from the upstream project before downloading, because backend dependencies and model IDs can change.

## Goals

- Install the `threedee` CLI.
- Configure OpenRouter without committing secrets.
- Install local GPU backends outside this repository.
- Wire those backends through ignored local config.
- Prove each stage with a small smoke test before attempting expensive full runs.

## Agent Posture

- Be proactive: inspect the machine, shell, Python versions, GPU visibility, CUDA/runtime support, existing model folders, and current config before asking setup questions.
- Ask only for decisions that require user approval, credentials, license acceptance, or long-running/large downloads.
- Keep external model repositories, checkpoints, caches, virtual environments, and generated runs out of git.
- Prefer ignored local config such as `threedee.local.toml` for machine-specific commands, paths, model names, endpoints, and secrets.
- Do not persist API keys, Hugging Face tokens, private paths, or machine-specific workarounds in tracked docs.
- Stop for user approval before installing system packages, downloading large checkpoints, accepting third-party licenses, or storing credentials.

## Bootstrap The Repository

Start here when setting up `threedee` on a new machine:

1. Choose or ask for a workspace directory.
2. Clone the repository:
   ```bash
   git clone https://github.com/rakanssh/threedee.git
   cd threedee
   ```
3. Read the project instructions:
   ```bash
   cat AGENTS.md
   cat README.md
   cat .agents/setup.md
   ```
4. Inspect the repo state:
   ```bash
   git status --short --branch
   python --version
   ```
5. Create and activate a Python environment for the CLI:
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
6. Verify the orchestrator before touching heavy backends:
   ```bash
   python -m compileall threedee
   threedee generate "smoke test asset" --dry-run
   threedee status
   ```

## User Inputs And Approvals

Use these project defaults:

- Store OpenRouter API keys in ignored `threedee.local.toml` via `threedee config set-openrouter --shared-api-key`.
- Keep `threedee.toml` as tracked defaults and put local commands/secrets in `threedee.local.toml`.
- Install model repositories, checkpoints, and caches outside this repository.
- Use `trellis2` as the primary mesh backend unless the user asks for another backend.
- Use `skintokens` as the primary rig backend unless the user asks for another backend.
- Start with fast/smoke-test backend settings, then increase quality after the pipeline works.

Ask the user only for:

- The OpenRouter API key.
- Permission before large downloads, system package installs, or long inference runs.
- Hugging Face license acceptance or gated model access when required.
- A preferred install/cache location if the default local tools/models directory is unsuitable.

## Configure OpenRouter

Inspect effective config:

```bash
threedee config show
```

Store OpenRouter settings in ignored local config:

```bash
threedee config set-openrouter --shared-api-key "..."
threedee config set-openrouter --llm-model "provider/model"
threedee config set-openrouter --image-model "provider/image-model"
```

Before local 3D setup, prove cloud stages:

```bash
threedee generate "single stylized knight, isolated, one view" --until spec
threedee generate "single stylized knight, isolated, one view" --until image
```

For riggable characters, guide reference prompts toward a single subject in a rigging-safe neutral A-pose with arms and hands separated from the torso.

## Backend Setup Contract

Install each backend independently before wiring it into `threedee`.

For each backend:

1. Read the backend's official install instructions.
2. Verify GPU/runtime compatibility.
3. Identify required model repositories and any gated access.
4. Authenticate in the same environment and OS user that will run inference.
5. Install the backend outside `threedee`.
6. Download checkpoints using the backend's supported method.
7. Run the backend manually on a known input.
8. Create a wrapper script that accepts the `threedee` placeholders.
9. Wire the wrapper into ignored local config.
10. Verify through `threedee` with the smallest useful run.

Every stage command should accept the relevant placeholders:

- `{input}`: stage input path
- `{output}`: artifact path the command must create
- `{run_dir}`: current run directory
- `{prompt}`: original user prompt, when useful
- `{seed}`: seed, if provided

Quote placeholders because paths may contain spaces. A command is successful only if it exits with code 0 and creates `{output}`. Wrappers should stream progress to stdout/stderr so `threedee` can show live progress while also preserving per-run logs.

## Mesh Backend Pattern

Use this pattern for image-to-3D backends such as TRELLIS.2 or Hunyuan3D:

1. Install the backend outside the repo.
2. Run its official image-to-mesh example manually.
3. Create a wrapper with this shape:
   ```bash
   backend-wrapper --input "{input}" --output "{output}" --seed "{seed}"
   ```
4. Start with a fast/low-resolution setting for the first proof.
5. Wire local config:
   ```toml
   [stages.mesh.<backend>]
   command = 'backend-wrapper --input "{input}" --output "{output}" --seed "{seed}"'
   output = "asset_raw.glb"
   ```
6. Verify:
   ```bash
   threedee generate "simple stylized prop, isolated, one view" --until mesh
   threedee status
   ```

Record tested backend repo commits, model IDs, and important package pins in local notes when reproducibility matters. Do not hardcode private paths in tracked files.

## Rig Backend Pattern

Use this pattern for mesh-to-rig backends such as SkinTokens or RigAnything:

1. Install the backend outside the repo.
2. Download its pretrained checkpoints.
3. Run a cheap import smoke test, including CUDA visibility and any required 3D import/export library.
4. Run the backend manually on a known mesh.
5. Create a wrapper with this shape:
   ```bash
   rig-wrapper --input "{input}" --output "{output}"
   ```
6. Wire local config:
   ```toml
   [stages.rig.<backend>]
   command = 'rig-wrapper --input "{input}" --output "{output}"'
   output = "asset_rigged.glb"
   ```
7. Verify:
   ```bash
   threedee benchmark rig <backend> <job_id>
   threedee status <job_id>
   ```

Rig backends expect a mesh input. For an existing mesh-only run, ensure the cleanup artifact exists first. If no cleanup command is configured, copying the raw mesh to the configured cleanup output is acceptable for a local resume.

## Prompt Guidance

For single-image mesh backends, ask image models for:

- exactly one subject or object
- exactly one view, preferably three-quarter front
- full body/object visible
- rigging-safe neutral A-pose for characters
- arms, hands, legs, clothing, armor, and props separated from the torso
- clean background, no text, no watermark

Avoid:

- character sheets
- front-and-side comparisons
- turnarounds
- split panels
- duplicate subjects
- hands touching the body
- crossed arms
- cloaks, props, or weapons bridging limbs to the torso

## Final Handoff And User Test

After setup, report what was configured:

- CLI install location and activation command.
- OpenRouter config status, without printing secrets.
- Mesh backend name and whether its manual smoke test passed.
- Rig backend name and whether its manual smoke test passed.
- Any model access, license, checkpoint, or version-pin notes the user should know.
- The exact local config file that contains machine-specific commands.

Then ask the user to run a small test from their own terminal:

```bash
threedee config show
threedee generate "smoke test asset" --dry-run
threedee generate "single riggable character, neutral A-pose, isolated" --until image
threedee status
```

If the user wants to test the local mesh backend, ask them to run:

```bash
threedee generate "single riggable character, neutral A-pose, isolated" --until mesh
threedee status
```

If the user wants to test the local rig backend after a mesh exists, ask them to run:

```bash
threedee benchmark rig skintokens <job_id>
threedee status <job_id>
```

For mesh tests, confirm the run folder contains:

- `reference.png`
- `asset_raw.glb`
- `mesh:<backend>.log`
- `manifest.json`

For rig tests, confirm the run folder contains:

- `asset_clean.glb` or another configured cleanup input
- `asset_rigged.glb`
- `rig:<backend>.log` or `benchmark_rig:<backend>.log`
- `manifest.json`

If a stage fails, read the stage log first. Fix the external backend command before changing the orchestrator unless the failure is clearly a `threedee` path, logging, or manifest bug.
