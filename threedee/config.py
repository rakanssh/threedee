from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import os
import tomllib


DEFAULT_CONFIG_PATH = Path("threedee.toml")
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"
DEFAULT_CHAT_COMPLETIONS_URL = f"{DEFAULT_BASE_URL}/chat/completions"


DEFAULT_CONFIG = """# threedee local pipeline config

[openrouter]
base_url = "https://openrouter.ai/api/v1"
llm_url = "https://openrouter.ai/api/v1/chat/completions"
image_url = "https://openrouter.ai/api/v1/chat/completions"
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
    llm_url: str
    image_url: str
    llm_model: str
    image_model: str
    api_key_env: str
    llm_api_key: str | None
    image_api_key: str | None
    app_title: str
    app_url: str

    @property
    def api_key(self) -> str | None:
        return self.llm_key

    @property
    def llm_key(self) -> str | None:
        return self.llm_api_key or os.environ.get(self.api_key_env)

    @property
    def image_key(self) -> str | None:
        return self.image_api_key or self.llm_key


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


def local_config_path(path: Path = DEFAULT_CONFIG_PATH) -> Path:
    if path.name == DEFAULT_CONFIG_PATH.name:
        return path.with_name("threedee.local.toml")
    return path.with_name(f"{path.stem}.local{path.suffix}")


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    raw: dict[str, Any] = {}
    if path.exists():
        raw = tomllib.loads(path.read_text(encoding="utf-8"))
    local_path = local_config_path(path)
    if local_path.exists():
        raw = _deep_merge(raw, tomllib.loads(local_path.read_text(encoding="utf-8")))

    openrouter = raw.get("openrouter", {})
    runs = raw.get("runs", {})
    stages = raw.get("stages", {})
    tools = raw.get("tools", {})

    mesh_raw = stages.get("mesh", {})
    rig_raw = stages.get("rig", {})
    cleanup_raw = stages.get("cleanup", {}).get("blender", {})

    base_url = str(openrouter.get("base_url", DEFAULT_BASE_URL)).rstrip("/")
    llm_url = str(openrouter.get("llm_url") or f"{base_url}/chat/completions")
    image_url = str(openrouter.get("image_url") or llm_url)

    return AppConfig(
        path=path,
        openrouter=OpenRouterConfig(
            base_url=base_url,
            llm_url=llm_url,
            image_url=image_url,
            llm_model=str(openrouter.get("llm_model", "google/gemini-3-flash-preview")),
            image_model=str(openrouter.get("image_model", "openai/gpt-5.4-image-2")),
            api_key_env=str(openrouter.get("api_key_env", "OPENROUTER_API_KEY")),
            llm_api_key=_optional_str(openrouter.get("llm_api_key")),
            image_api_key=_optional_str(openrouter.get("image_api_key")),
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


def set_local_openrouter_config(path: Path, values: dict[str, str]) -> Path:
    local_path = local_config_path(path)
    raw: dict[str, Any] = {}
    if local_path.exists():
        raw = tomllib.loads(local_path.read_text(encoding="utf-8"))
    openrouter = raw.setdefault("openrouter", {})
    if not isinstance(openrouter, dict):
        raise ValueError("[openrouter] in local config must be a table")
    openrouter.update(values)
    local_path.write_text(_format_toml(raw), encoding="utf-8")
    return local_path


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text or None


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge(current, value)
        else:
            merged[key] = value
    return merged


def _format_toml(raw: dict[str, Any]) -> str:
    lines: list[str] = ["# Local threedee config. This file is ignored by git.", ""]
    scalars = {key: value for key, value in raw.items() if not isinstance(value, dict)}
    for key, value in scalars.items():
        lines.append(f"{key} = {_toml_value(value)}")
    if scalars:
        lines.append("")
    for key, value in raw.items():
        if isinstance(value, dict):
            _append_toml_table(lines, [key], value)
    return "\n".join(lines).rstrip() + "\n"


def _append_toml_table(lines: list[str], path: list[str], values: dict[str, Any]) -> None:
    scalar_values = {key: value for key, value in values.items() if not isinstance(value, dict)}
    if scalar_values:
        lines.append(f"[{'.'.join(path)}]")
        for key, value in scalar_values.items():
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    for key, value in values.items():
        if isinstance(value, dict):
            _append_toml_table(lines, [*path, key], value)


def _toml_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    return '"' + str(value).replace("\\", "\\\\").replace('"', '\\"') + '"'
