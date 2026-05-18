from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import json


MANIFEST_FILE = "manifest.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_manifest(
    *,
    job_id: str,
    prompt: str,
    run_dir: Path,
    seed: int | None,
    models: dict[str, str],
    dry_run: bool,
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "prompt": prompt,
        "seed": seed,
        "dry_run": dry_run,
        "status": "created",
        "created_at": utc_now(),
        "updated_at": utc_now(),
        "run_dir": str(run_dir),
        "models": models,
        "stages": {},
        "artifacts": {},
        "errors": [],
    }


def manifest_path(run_dir: Path) -> Path:
    return run_dir / MANIFEST_FILE


def load_manifest(run_dir: Path) -> dict[str, Any]:
    return json.loads(manifest_path(run_dir).read_text(encoding="utf-8"))


def save_manifest(run_dir: Path, manifest: dict[str, Any]) -> None:
    manifest["updated_at"] = utc_now()
    manifest_path(run_dir).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def set_status(manifest: dict[str, Any], status: str) -> None:
    manifest["status"] = status


def stage_started(manifest: dict[str, Any], name: str) -> None:
    manifest["stages"][name] = {
        "status": "running",
        "started_at": utc_now(),
    }


def stage_done(
    manifest: dict[str, Any],
    name: str,
    *,
    artifact: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> None:
    stage = manifest["stages"].setdefault(name, {})
    stage["status"] = "done"
    stage["finished_at"] = utc_now()
    if artifact is not None:
        stage["artifact"] = artifact
        manifest["artifacts"][name] = artifact
    if metadata:
        stage["metadata"] = metadata


def stage_skipped(manifest: dict[str, Any], name: str, reason: str) -> None:
    manifest["stages"][name] = {
        "status": "skipped",
        "reason": reason,
        "finished_at": utc_now(),
    }


def stage_failed(manifest: dict[str, Any], name: str, error: str) -> None:
    manifest["stages"][name] = {
        "status": "failed",
        "error": error,
        "finished_at": utc_now(),
    }
    manifest["errors"].append({"stage": name, "error": error, "at": utc_now()})
    manifest["status"] = "failed"
