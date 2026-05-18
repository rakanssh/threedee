from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os
import tomllib


DEFAULT_CONFIG_PATH = Path("threedee.toml")


DEFAULT_CONFIG = """# threedee local pipeline config

[openrouter]
base_url = "https://openrouter.ai/api/v1"
llm_model = "google/gemini-3-flash-preview"
image_model = "openai/gpt-5.4-image-2"
api_key_env = "OPENROUTER_API_KEY"
app_title = "threedee"
app_url = "https://github.com/rakanssh/threedee"

[runs]
dir = "runs"

[stages.mesh.trellis2]
# Fill this in on the target GPU machine after installing TRELLIS.2.
# Available placeholders: {input}, {output}, {run_dir}, {prompt}, {seed}
command = ""
output = "asset_raw.glb"

[stages.mesh.hunyuan3d]
# Optional benchmark backend.
command = ""
output = "asset_raw_hunyuan.glb"

[stages.cleanup.blender]
# Optional. If empty, the raw mesh is copied forward as asset_clean.glb.
# Available placeholders: {input}, {output}, {run_dir}
command = ""
output = "asset_clean.glb"

[stages.rig.skintokens]
# Fill this in on the target GPU machine after installing SkinTokens.
# Available placeholders: {input}, {output}, {run_dir}
command = ""
output = "asset_rigged.glb"

[stages.rig.riganything]
# Optional benchmark backend.
command = ""
output = "asset_rigged_riganything.glb"

[tools]
# Optional final validator command. Available placeholders: {input}, {output}, {run_dir}
gltf_validator = ""
"""


@dataclass(frozen=True)
class OpenRouterConfig:
    base_url: str
    llm_model: str
    image_model: str
    api_key_env: str
    app_title: str
    app_url: str

    @property
    def api_key(self) -> str | None:
        return os.environ.get(self.api_key_env)


@dataclass(frozen=True)
class StageConfig:
    command: str
    output: str


@dataclass(frozen=True)
class AppConfig:
    path: Path
    openrouter: OpenRouterConfig
    runs_dir: Path
    mesh_stages: dict[str, StageConfig]
    cleanup_stage: StageConfig
    rig_stages: dict[str, StageConfig]
    gltf_validator: str


def write_default_config(path: Path = DEFAULT_CONFIG_PATH) -> None:
    if path.exists():
        raise FileExistsError(f"Config already exists: {path}")
    path.write_text(DEFAULT_CONFIG, encoding="utf-8")


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    raw: dict[str, Any] = {}
    if path.exists():
        raw = tomllib.loads(path.read_text(encoding="utf-8"))

    openrouter = raw.get("openrouter", {})
    runs = raw.get("runs", {})
    stages = raw.get("stages", {})
    tools = raw.get("tools", {})

    mesh_raw = stages.get("mesh", {})
    rig_raw = stages.get("rig", {})
    cleanup_raw = stages.get("cleanup", {}).get("blender", {})

    return AppConfig(
        path=path,
        openrouter=OpenRouterConfig(
            base_url=str(openrouter.get("base_url", "https://openrouter.ai/api/v1")).rstrip("/"),
            llm_model=str(openrouter.get("llm_model", "google/gemini-3-flash-preview")),
            image_model=str(openrouter.get("image_model", "openai/gpt-5.4-image-2")),
            api_key_env=str(openrouter.get("api_key_env", "OPENROUTER_API_KEY")),
            app_title=str(openrouter.get("app_title", "threedee")),
            app_url=str(openrouter.get("app_url", "https://github.com/rakanssh/threedee")),
        ),
        runs_dir=Path(str(runs.get("dir", "runs"))),
        mesh_stages={
            name: StageConfig(
                command=str(value.get("command", "")),
                output=str(value.get("output", f"asset_raw_{name}.glb")),
            )
            for name, value in mesh_raw.items()
        }
        or {
            "trellis2": StageConfig(command="", output="asset_raw.glb"),
            "hunyuan3d": StageConfig(command="", output="asset_raw_hunyuan.glb"),
        },
        cleanup_stage=StageConfig(
            command=str(cleanup_raw.get("command", "")),
            output=str(cleanup_raw.get("output", "asset_clean.glb")),
        ),
        rig_stages={
            name: StageConfig(
                command=str(value.get("command", "")),
                output=str(value.get("output", f"asset_rigged_{name}.glb")),
            )
            for name, value in rig_raw.items()
        }
        or {
            "skintokens": StageConfig(command="", output="asset_rigged.glb"),
            "riganything": StageConfig(command="", output="asset_rigged_riganything.glb"),
        },
        gltf_validator=str(tools.get("gltf_validator", "")),
    )
