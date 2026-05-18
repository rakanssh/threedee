from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any
import base64
import os
import re
import shutil
import subprocess
import sys

from .config import AppConfig, StageConfig
from .manifest import (
    load_manifest,
    new_manifest,
    save_manifest,
    set_status,
    stage_done,
    stage_failed,
    stage_skipped,
    stage_started,
)
from .openrouter import OpenRouterClient, OpenRouterError, save_json


UNTIL_ORDER = ["spec", "image", "mesh", "clean", "rig", "validate", "all"]

PLACEHOLDER_PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/p9sAAAAASUVORK5CYII="
)


class PipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class GenerateOptions:
    prompt: str
    config: AppConfig
    seed: int | None
    job_id: str | None
    dry_run: bool
    until: str
    mesh_backend: str
    rig_backend: str
    input_image: Path | None


def generate(options: GenerateOptions) -> Path:
    if options.until not in UNTIL_ORDER:
        raise PipelineError(f"Unknown --until value: {options.until}")

    run_dir = _create_run_dir(options.config.runs_dir, options.job_id, options.prompt)
    run_dir.mkdir(parents=True, exist_ok=False)

    manifest = new_manifest(
        job_id=run_dir.name,
        prompt=options.prompt,
        run_dir=run_dir,
        seed=options.seed,
        dry_run=options.dry_run,
        models={
            "llm": f"openrouter:{options.config.openrouter.llm_model}",
            "image": f"openrouter:{options.config.openrouter.image_model}",
            "mesh": f"local:{options.mesh_backend}",
            "rig": f"local:{options.rig_backend}",
        },
    )
    save_manifest(run_dir, manifest)

    try:
        client = None if options.dry_run else OpenRouterClient(options.config.openrouter)
        spec = _run_spec(run_dir, manifest, options, client)
        if _stop_after(options.until, "spec"):
            set_status(manifest, "completed")
            save_manifest(run_dir, manifest)
            return run_dir

        reference = _run_image(run_dir, manifest, options, client, spec)
        if _stop_after(options.until, "image"):
            set_status(manifest, "completed")
            save_manifest(run_dir, manifest)
            return run_dir

        raw_mesh = _run_configured_stage(
            run_dir=run_dir,
            manifest=manifest,
            stage_name=f"mesh:{options.mesh_backend}",
            config=_stage(options.config.mesh_stages, options.mesh_backend, "mesh"),
            input_path=reference,
            prompt=options.prompt,
            seed=options.seed,
            dry_run=options.dry_run,
            required=True,
        )
        if _stop_after(options.until, "mesh"):
            set_status(manifest, "completed")
            save_manifest(run_dir, manifest)
            return run_dir

        clean_mesh = _run_cleanup(run_dir, manifest, options.config.cleanup_stage, raw_mesh, options.dry_run)
        if _stop_after(options.until, "clean"):
            set_status(manifest, "completed")
            save_manifest(run_dir, manifest)
            return run_dir

        rigged_mesh = _run_configured_stage(
            run_dir=run_dir,
            manifest=manifest,
            stage_name=f"rig:{options.rig_backend}",
            config=_stage(options.config.rig_stages, options.rig_backend, "rig"),
            input_path=clean_mesh,
            prompt=options.prompt,
            seed=options.seed,
            dry_run=options.dry_run,
            required=True,
        )
        if _stop_after(options.until, "rig"):
            set_status(manifest, "completed")
            save_manifest(run_dir, manifest)
            return run_dir

        _run_validation(run_dir, manifest, options.config.gltf_validator, rigged_mesh, options.dry_run)
        set_status(manifest, "completed")
        save_manifest(run_dir, manifest)
        return run_dir
    except Exception as exc:
        set_status(manifest, "failed")
        manifest["errors"].append({"stage": "pipeline", "error": str(exc)})
        save_manifest(run_dir, manifest)
        raise


def benchmark_mesh(config: AppConfig, run_dir: Path, backend: str, dry_run: bool = False) -> Path:
    manifest = load_manifest(run_dir)
    reference = Path(manifest["artifacts"].get("image", run_dir / "reference.png"))
    if not reference.is_absolute():
        reference = run_dir / reference
    return _run_configured_stage(
        run_dir=run_dir,
        manifest=manifest,
        stage_name=f"benchmark_mesh:{backend}",
        config=_stage(config.mesh_stages, backend, "mesh"),
        input_path=reference,
        prompt=str(manifest.get("prompt", "")),
        seed=manifest.get("seed"),
        dry_run=dry_run,
        required=True,
    )


def benchmark_rig(config: AppConfig, run_dir: Path, backend: str, dry_run: bool = False) -> Path:
    manifest = load_manifest(run_dir)
    clean = Path(manifest["artifacts"].get("clean", run_dir / config.cleanup_stage.output))
    if not clean.is_absolute():
        clean = run_dir / clean
    return _run_configured_stage(
        run_dir=run_dir,
        manifest=manifest,
        stage_name=f"benchmark_rig:{backend}",
        config=_stage(config.rig_stages, backend, "rig"),
        input_path=clean,
        prompt=str(manifest.get("prompt", "")),
        seed=manifest.get("seed"),
        dry_run=dry_run,
        required=True,
    )


def latest_run(runs_dir: Path) -> Path | None:
    if not runs_dir.exists():
        return None
    runs = [path for path in runs_dir.iterdir() if path.is_dir() and (path / "manifest.json").exists()]
    return max(runs, key=lambda path: path.stat().st_mtime) if runs else None


def list_runs(runs_dir: Path) -> list[dict[str, Any]]:
    if not runs_dir.exists():
        return []
    rows: list[dict[str, Any]] = []
    for path in sorted(runs_dir.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True):
        if path.is_dir() and (path / "manifest.json").exists():
            try:
                manifest = load_manifest(path)
            except Exception:
                continue
            rows.append(
                {
                    "job_id": manifest.get("job_id", path.name),
                    "status": manifest.get("status", "unknown"),
                    "prompt": manifest.get("prompt", ""),
                    "updated_at": manifest.get("updated_at", ""),
                    "run_dir": str(path),
                }
            )
    return rows


def open_path(path: Path) -> None:
    if sys.platform == "win32":
        os.startfile(path)  # type: ignore[attr-defined]
    elif sys.platform == "darwin":
        subprocess.run(["open", str(path)], check=False)
    else:
        subprocess.run(["xdg-open", str(path)], check=False)


def _run_spec(
    run_dir: Path,
    manifest: dict[str, Any],
    options: GenerateOptions,
    client: OpenRouterClient | None,
) -> dict[str, Any]:
    stage_started(manifest, "spec")
    save_manifest(run_dir, manifest)
    spec_path = run_dir / "asset_spec.json"
    try:
        if options.dry_run:
            spec = {
                "prompt": options.prompt,
                "asset": options.prompt,
                "pose": "neutral rest pose",
                "image_prompt": f"{options.prompt}, isolated single 3D game asset reference, clean background",
                "negative_prompt": "cropped, extra limbs, multiple subjects, text, watermark",
            }
        else:
            assert client is not None
            spec = client.asset_spec(prompt=options.prompt, model=options.config.openrouter.llm_model)
        save_json(spec_path, spec)
        stage_done(manifest, "spec", artifact=str(spec_path), metadata={"model": options.config.openrouter.llm_model})
        save_manifest(run_dir, manifest)
        return spec
    except Exception as exc:
        stage_failed(manifest, "spec", str(exc))
        save_manifest(run_dir, manifest)
        raise


def _run_image(
    run_dir: Path,
    manifest: dict[str, Any],
    options: GenerateOptions,
    client: OpenRouterClient | None,
    spec: dict[str, Any],
) -> Path:
    stage_started(manifest, "image")
    save_manifest(run_dir, manifest)
    output = run_dir / "reference.png"
    try:
        if options.input_image:
            shutil.copyfile(options.input_image, output)
            stage_done(manifest, "image", artifact=str(output), metadata={"source": str(options.input_image)})
        elif options.dry_run:
            output.write_bytes(PLACEHOLDER_PNG)
            stage_done(manifest, "image", artifact=str(output), metadata={"source": "dry_run_placeholder"})
        else:
            assert client is not None
            prompt = _image_prompt(options.prompt, spec)
            result = client.reference_image(prompt=prompt, model=options.config.openrouter.image_model)
            output.write_bytes(result.image_bytes)
            save_json(run_dir / "openrouter_image_response.json", result.raw_response)
            if result.text:
                (run_dir / "image_response.txt").write_text(result.text, encoding="utf-8")
            stage_done(
                manifest,
                "image",
                artifact=str(output),
                metadata={"model": options.config.openrouter.image_model, "prompt": prompt},
            )
        save_manifest(run_dir, manifest)
        return output
    except Exception as exc:
        stage_failed(manifest, "image", str(exc))
        save_manifest(run_dir, manifest)
        raise


def _run_cleanup(
    run_dir: Path,
    manifest: dict[str, Any],
    config: StageConfig,
    raw_mesh: Path,
    dry_run: bool,
) -> Path:
    stage_name = "clean"
    output = run_dir / config.output
    if not config.command:
        stage_started(manifest, stage_name)
        shutil.copyfile(raw_mesh, output)
        stage_done(manifest, stage_name, artifact=str(output), metadata={"mode": "copy_raw_mesh"})
        save_manifest(run_dir, manifest)
        return output
    return _run_configured_stage(
        run_dir=run_dir,
        manifest=manifest,
        stage_name=stage_name,
        config=config,
        input_path=raw_mesh,
        prompt="",
        seed=None,
        dry_run=dry_run,
        required=False,
    )


def _run_validation(
    run_dir: Path,
    manifest: dict[str, Any],
    command: str,
    rigged_mesh: Path,
    dry_run: bool,
) -> None:
    stage_name = "validate"
    if not command:
        stage_skipped(manifest, stage_name, "No glTF validator command configured")
        save_manifest(run_dir, manifest)
        return
    config = StageConfig(command=command, output="validation_report.json")
    _run_configured_stage(
        run_dir=run_dir,
        manifest=manifest,
        stage_name=stage_name,
        config=config,
        input_path=rigged_mesh,
        prompt="",
        seed=None,
        dry_run=dry_run,
        required=False,
    )


def _run_configured_stage(
    *,
    run_dir: Path,
    manifest: dict[str, Any],
    stage_name: str,
    config: StageConfig,
    input_path: Path,
    prompt: str,
    seed: int | None,
    dry_run: bool,
    required: bool,
) -> Path:
    output = run_dir / config.output
    stage_started(manifest, stage_name)
    save_manifest(run_dir, manifest)

    if dry_run:
        output.write_bytes(b"dry-run placeholder artifact\n")
        stage_done(manifest, stage_name, artifact=str(output), metadata={"mode": "dry_run"})
        save_manifest(run_dir, manifest)
        return output

    if not config.command:
        message = f"No command configured for {stage_name}. Edit threedee.toml."
        if required:
            stage_failed(manifest, stage_name, message)
            save_manifest(run_dir, manifest)
            raise PipelineError(message)
        stage_skipped(manifest, stage_name, message)
        save_manifest(run_dir, manifest)
        return input_path

    command = _format_command(
        config.command,
        input_path=input_path,
        output_path=output,
        run_dir=run_dir,
        prompt=prompt,
        seed=seed,
    )
    log_path = run_dir / f"{_safe_stage_name(stage_name)}.log"
    with log_path.open("w", encoding="utf-8") as log:
        log.write(f"$ {command}\n\n")
        completed = subprocess.run(
            command,
            cwd=run_dir,
            shell=True,
            stdout=log,
            stderr=subprocess.STDOUT,
            text=True,
        )
    if completed.returncode != 0:
        error = f"{stage_name} command exited {completed.returncode}. See {log_path}"
        stage_failed(manifest, stage_name, error)
        save_manifest(run_dir, manifest)
        raise PipelineError(error)
    if not output.exists():
        error = f"{stage_name} did not create expected output: {output}"
        stage_failed(manifest, stage_name, error)
        save_manifest(run_dir, manifest)
        raise PipelineError(error)

    stage_done(manifest, stage_name, artifact=str(output), metadata={"log": str(log_path), "command": command})
    save_manifest(run_dir, manifest)
    return output


def _format_command(
    template: str,
    *,
    input_path: Path,
    output_path: Path,
    run_dir: Path,
    prompt: str,
    seed: int | None,
) -> str:
    values = {
        "input": str(input_path.resolve()),
        "output": str(output_path.resolve()),
        "run_dir": str(run_dir.resolve()),
        "prompt": prompt.replace('"', '\\"'),
        "seed": "" if seed is None else str(seed),
    }
    try:
        return template.format(**values)
    except KeyError as exc:
        raise PipelineError(f"Unknown command placeholder: {exc}") from exc


def _stage(stages: dict[str, StageConfig], backend: str, kind: str) -> StageConfig:
    if backend not in stages:
        available = ", ".join(sorted(stages)) or "none"
        raise PipelineError(f"Unknown {kind} backend '{backend}'. Available: {available}")
    return stages[backend]


def _image_prompt(prompt: str, spec: dict[str, Any]) -> str:
    image_prompt = spec.get("image_prompt") or spec.get("reference_image_prompt")
    negative = spec.get("negative_prompt")
    if not image_prompt:
        image_prompt = (
            f"{prompt}, single isolated 3D asset concept, full body or complete object, "
            "neutral rest pose, three-quarter front view, clean white background, no text"
        )
    if negative:
        image_prompt = f"{image_prompt}\nAvoid: {negative}"
    return str(image_prompt)


def _create_run_dir(runs_dir: Path, job_id: str | None, prompt: str) -> Path:
    if job_id:
        return runs_dir / job_id
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^a-z0-9]+", "-", prompt.lower()).strip("-")[:48] or "asset"
    return runs_dir / f"asset_{stamp}_{slug}"


def _stop_after(until: str, stage: str) -> bool:
    return until != "all" and UNTIL_ORDER.index(stage) >= UNTIL_ORDER.index(until)


def _safe_stage_name(name: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", name)
