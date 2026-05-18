from __future__ import annotations

from pathlib import Path
import argparse
import json
import sys

from .config import DEFAULT_CONFIG_PATH, load_config, write_default_config
from .manifest import load_manifest
from .pipeline import (
    GenerateOptions,
    PipelineError,
    benchmark_mesh,
    benchmark_rig,
    generate,
    latest_run,
    list_runs,
    open_path,
)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except (PipelineError, FileExistsError, FileNotFoundError, KeyError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="threedee", description="Prompt-to-rigged-3D asset pipeline CLI.")
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH, help="Path to threedee.toml.")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="Write a default threedee.toml config.")
    init.set_defaults(func=cmd_init)

    generate_cmd = sub.add_parser("generate", help="Generate a rigged 3D asset run.")
    generate_cmd.add_argument("prompt", help="Asset prompt.")
    generate_cmd.add_argument("--seed", type=int, default=None)
    generate_cmd.add_argument("--job-id", default=None)
    generate_cmd.add_argument("--dry-run", action="store_true", help="Create placeholder artifacts without API/model calls.")
    generate_cmd.add_argument("--until", choices=["spec", "image", "mesh", "clean", "rig", "validate", "all"], default="all")
    generate_cmd.add_argument("--mesh", default="trellis2", help="Mesh backend from threedee.toml.")
    generate_cmd.add_argument("--rig", default="skintokens", help="Rig backend from threedee.toml.")
    generate_cmd.add_argument("--image", type=Path, default=None, help="Use an existing reference image instead of generating one.")
    generate_cmd.set_defaults(func=cmd_generate)

    status = sub.add_parser("status", help="Show run status.")
    status.add_argument("job_id", nargs="?", help="Run id. Defaults to latest run.")
    status.add_argument("--json", action="store_true", help="Print full manifest JSON.")
    status.set_defaults(func=cmd_status)

    list_cmd = sub.add_parser("list", help="List recent runs.")
    list_cmd.set_defaults(func=cmd_list)

    open_cmd = sub.add_parser("open", help="Open a run directory in the OS file browser.")
    open_cmd.add_argument("job_id", nargs="?", help="Run id. Defaults to latest run.")
    open_cmd.set_defaults(func=cmd_open)

    bench = sub.add_parser("benchmark", help="Run an alternate mesh or rig backend on an existing run.")
    bench.add_argument("kind", choices=["mesh", "rig"])
    bench.add_argument("backend", help="Backend name from threedee.toml.")
    bench.add_argument("job_id", nargs="?", help="Run id. Defaults to latest run.")
    bench.add_argument("--dry-run", action="store_true")
    bench.set_defaults(func=cmd_benchmark)

    return parser


def cmd_init(args: argparse.Namespace) -> int:
    write_default_config(args.config)
    print(f"wrote {args.config}")
    return 0


def cmd_generate(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    run_dir = generate(
        GenerateOptions(
            prompt=args.prompt,
            config=config,
            seed=args.seed,
            job_id=args.job_id,
            dry_run=args.dry_run,
            until=args.until,
            mesh_backend=args.mesh,
            rig_backend=args.rig,
            input_image=args.image,
        )
    )
    manifest = load_manifest(run_dir)
    print(f"{manifest['status']}: {manifest['job_id']}")
    print(run_dir)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    run_dir = _resolve_run_dir(config.runs_dir, args.job_id)
    manifest = load_manifest(run_dir)
    if args.json:
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    print(f"{manifest.get('job_id')}: {manifest.get('status')}")
    print(f"prompt: {manifest.get('prompt')}")
    print(f"run_dir: {run_dir}")
    for name, stage in manifest.get("stages", {}).items():
        status = stage.get("status", "unknown")
        detail = stage.get("artifact") or stage.get("reason") or stage.get("error") or ""
        print(f"- {name}: {status} {detail}")
    if manifest.get("errors"):
        print("errors:")
        for error in manifest["errors"]:
            print(f"- {error.get('stage')}: {error.get('error')}")
    return 0


def cmd_list(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    rows = list_runs(config.runs_dir)
    if not rows:
        print("no runs")
        return 0
    for row in rows:
        prompt = str(row["prompt"])
        if len(prompt) > 70:
            prompt = prompt[:67] + "..."
        print(f"{row['job_id']}  {row['status']:<10}  {prompt}")
    return 0


def cmd_open(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    run_dir = _resolve_run_dir(config.runs_dir, args.job_id)
    open_path(run_dir)
    print(run_dir)
    return 0


def cmd_benchmark(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    run_dir = _resolve_run_dir(config.runs_dir, args.job_id)
    if args.kind == "mesh":
        output = benchmark_mesh(config, run_dir, args.backend, dry_run=args.dry_run)
    else:
        output = benchmark_rig(config, run_dir, args.backend, dry_run=args.dry_run)
    print(output)
    return 0


def _resolve_run_dir(runs_dir: Path, job_id: str | None) -> Path:
    if job_id:
        run_dir = runs_dir / job_id
    else:
        latest = latest_run(runs_dir)
        if latest is None:
            raise FileNotFoundError(f"No runs found in {runs_dir}")
        run_dir = latest
    if not run_dir.exists():
        raise FileNotFoundError(f"Run not found: {run_dir}")
    return run_dir


if __name__ == "__main__":
    raise SystemExit(main())
