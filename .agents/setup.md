# Setup Playbook

Use this when helping a user bring up `threedee` on a local GPU machine.

## Agent Posture

- Be proactive: inspect the machine, installed tools, GPU visibility, Python versions, existing model folders, and current config before asking questions.
- Make conservative defaults when the user has no preference: keep external repos/checkpoints outside `threedee`, use ignored local config, and start with the fastest backend settings that prove the pipeline.
- Ask only for decisions that affect local ownership or cost: install location, API key storage, model/provider choice, and whether to run expensive downloads/inference.
- After each backend install, verify it manually before wiring `threedee`.
- Do not persist secrets, checkpoint tokens, or machine-private paths in tracked docs.
- Treat gated model access as part of setup, not as a runtime surprise. Check every upstream model a backend loads and ask the user to accept licenses or request access before long test runs.

## Setup Order

1. Verify the orchestrator first:
   ```bash
   python -m compileall threedee
   python -m threedee.cli generate "smoke test asset" --dry-run
   python -m threedee.cli status
   ```
2. Install editable if the user wants the `threedee` console command:
   ```bash
   python -m pip install -e .
   ```
3. Configure OpenRouter:
   ```bash
   threedee config show
   threedee config set-openrouter --shared-api-key "..."
   threedee config set-openrouter --llm-model "provider/model"
   threedee config set-openrouter --image-model "provider/image-model"
   ```
4. Test cloud stages before local 3D:
   ```bash
   threedee generate "single stylized knight, isolated, one view" --until spec
   threedee generate "single stylized knight, isolated, one view" --until image
   ```
5. Install local mesh, cleanup, rigging, and validation tools one at a time.
6. Confirm gated model access and authentication in the exact environment/user that will run the backend command.
7. Wire each working local command into ignored `threedee.local.toml` or another untracked config passed with `--config`.

If the user asks you to install a backend and the next step is clear, continue through install, manual smoke test, wrapper creation, local config wiring, and `threedee --until <stage>` verification. Stop only for approvals, credentials, paid API/model downloads, or an environment decision that cannot be inferred.

## What To Ask The User

- Where should large model repos and checkpoints live?
- Which mesh backend should be primary, and which should be benchmark-only?
- Which rigging backend should be primary?
- Should API keys be stored in ignored local config or environment variables?
- Does the selected image model support image-only output, image+text output, or a provider-specific endpoint?
- What artifact quality target should the first pass use: fast smoke test or high-quality output?
- Does the selected local backend require gated model access or license acceptance?
- Should backend checkpoints be pinned to specific model IDs/revisions for reproducibility?

If the user does not care, choose a conventional local tools/models directory outside the repo and record only the generic pattern, not private paths, in tracked notes.

## Local Stage Contract

Every configured command should accept placeholders from `threedee.toml`:

- `{input}`: stage input path
- `{output}`: artifact path the command must create
- `{run_dir}`: current run directory
- `{prompt}`: original user prompt, when useful
- `{seed}`: seed, if provided

Quote placeholders in commands because paths may contain spaces. The command is successful only if it exits with code 0 and creates `{output}`.

Wrappers should stream meaningful progress to stdout/stderr and preserve backend logs. This is especially important during first runs, when dependency downloads and checkpoint loading may take a long time before GPU utilization is visible.

## TRELLIS.2 Mesh Setup Pattern

Use the official TRELLIS.2 install instructions for the target environment. Keep the TRELLIS.2 repo and checkpoints outside `threedee`.

Recommended flow:

1. Verify GPU and CUDA/PyTorch compatibility.
2. Identify every upstream model the selected TRELLIS.2 configuration loads. Request/accept gated model access before the first full run, and authenticate from the same local environment/user that will execute TRELLIS.2.
3. Record the main TRELLIS.2 model ID and any important auxiliary model IDs or revisions in local agent notes. Prefer pinned revisions when reproducing a known-good environment.
4. Install TRELLIS.2 and get its example image-to-GLB path working manually.
5. Create a small wrapper that accepts `--input`, `--output`, and `--seed`.
6. Start with the fastest supported pipeline/resolution to prove the CLI contract.
7. Wire the wrapper into local config:
   ```toml
   [stages.mesh.trellis2]
   command = 'path/to/wrapper --input "{input}" --output "{output}" --seed "{seed}"'
   output = "asset_raw.glb"
   ```

Avoid baking machine-specific paths into tracked files. Prefer ignored local config for actual commands.

Common TRELLIS.2 setup issues:

- Gated auxiliary models can fail after the main checkpoint downloads successfully. Read the stage log and request access to the specific model named in the error.
- Backend code may assume a particular version of libraries such as `transformers`, `trimesh`, or `Pillow`. Prefer minimal compatibility shims or version pins in the backend environment rather than changing the `threedee` orchestrator.
- GLB export may expose optional image codec issues. If a compressed texture extension fails, retry plain GLB export before changing mesh generation.

## Prompt/Image Guidance

For single-image mesh backends, ask image models for:

- exactly one subject or object
- exactly one view, preferably three-quarter front
- full body/object visible, neutral pose for riggable subjects
- clean background, no text or watermark

Avoid:

- character sheets
- front-and-side comparisons
- turnarounds
- split panels
- duplicate subjects

## Verification

After wiring a mesh command:

```bash
threedee generate "simple stylized prop, isolated, one view" --until mesh
threedee status
```

Check the run folder for:

- `reference.png`
- `asset_raw.glb`
- `mesh:<backend>.log`
- `manifest.json`

If a stage fails, read the stage log first and fix the external command before changing the orchestrator.
