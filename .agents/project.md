# Project Context

## Goal

Build a prompt-to-rigged-3D generation pipeline with a clear separation between orchestration, reference image generation, mesh generation, rigging, and validation.

OpenRouter provides LLM and 2D reference image calls. The 3D path runs locally in the configured GPU environment.

## Architecture

The repository is currently an orchestrator, not a model repo:

```text
threedee CLI
  -> OpenRouter asset spec
  -> OpenRouter reference image
  -> configured local mesh command
  -> configured local cleanup command or copy-through
  -> configured local rig command
  -> optional glTF validation
```

Local model commands are configured in `threedee.toml`.

## Model Direction

Primary path:

- Mesh: TRELLIS.2
- Rigging: SkinTokens / TokenRig

Benchmark path:

- Mesh: Hunyuan3D-2.1
- Rigging: RigAnything

Model and tool choices are selected for practical local evaluation and pipeline quality.

## Artifact Strategy

Every run writes to `runs/<job_id>/`.

Core artifacts:

- `manifest.json`
- `asset_spec.json`
- `reference.png`
- `asset_raw.glb`
- `asset_clean.glb`
- `asset_rigged.glb`
- stage logs

`runs/` is ignored by git.
