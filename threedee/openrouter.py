from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any
import base64
import json
import re
import urllib.error
import urllib.request

from .config import OpenRouterConfig


class OpenRouterError(RuntimeError):
    pass


@dataclass(frozen=True)
class ImageResult:
    image_bytes: bytes
    raw_response: dict[str, Any]
    text: str | None = None


class OpenRouterClient:
    def __init__(self, config: OpenRouterConfig):
        self.config = config
        if not config.api_key:
            raise OpenRouterError(f"Missing API key env var: {config.api_key_env}")

    def chat(self, *, model: str, messages: list[dict[str, Any]], extra: dict[str, Any] | None = None) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
        }
        if extra:
            payload.update(extra)
        return self._post_json("/chat/completions", payload)

    def asset_spec(self, *, prompt: str, model: str) -> dict[str, Any]:
        system = (
            "You turn short user prompts into structured 3D asset generation specs. "
            "Return only JSON. Do not wrap it in markdown."
        )
        user = {
            "prompt": prompt,
            "requirements": [
                "single 3D asset",
                "isolated full body/object reference",
                "neutral A-pose or rest pose if the subject can be rigged",
                "clear materials and silhouette",
                "negative prompt for unwanted artifacts",
            ],
        }
        response = self.chat(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": json.dumps(user)},
            ],
            extra={"temperature": 0.4},
        )
        content = _first_text(response)
        if not content:
            raise OpenRouterError("LLM response did not contain text content")
        return _parse_jsonish(content)

    def reference_image(self, *, prompt: str, model: str) -> ImageResult:
        response = self.chat(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            extra={"modalities": ["image", "text"]},
        )
        image_bytes = _extract_image_bytes(response)
        text = _first_text(response)
        return ImageResult(image_bytes=image_bytes, raw_response=response, text=text)

    def _post_json(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.config.base_url + path,
            data=body,
            method="POST",
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": self.config.app_url,
                "X-Title": self.config.app_title,
            },
        )
        try:
            with urllib.request.urlopen(request, timeout=300) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace")
            raise OpenRouterError(f"OpenRouter HTTP {exc.code}: {details}") from exc
        except urllib.error.URLError as exc:
            raise OpenRouterError(f"OpenRouter request failed: {exc}") from exc


def save_json(path: Path, value: dict[str, Any]) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _first_text(response: dict[str, Any]) -> str | None:
    choices = response.get("choices") or []
    if not choices:
        return None
    message = choices[0].get("message") or {}
    content = message.get("content")
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts) if parts else None
    return None


def _parse_jsonish(content: str) -> dict[str, Any]:
    cleaned = content.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", cleaned, re.DOTALL)
    if fenced:
        cleaned = fenced.group(1).strip()
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise OpenRouterError(f"LLM response was not valid JSON: {content[:500]}") from exc
    if not isinstance(parsed, dict):
        raise OpenRouterError("LLM JSON response was not an object")
    return parsed


def _extract_image_bytes(response: dict[str, Any]) -> bytes:
    urls = list(_iter_image_urls(response))
    if not urls:
        raise OpenRouterError("Image response did not contain an image URL or data URL")
    return _load_image_url(urls[0])


def _iter_image_urls(value: Any):
    if isinstance(value, dict):
        image_url = value.get("image_url")
        if isinstance(image_url, str):
            yield image_url
        elif isinstance(image_url, dict) and isinstance(image_url.get("url"), str):
            yield image_url["url"]
        if isinstance(value.get("url"), str) and _looks_like_image_url(value["url"]):
            yield value["url"]
        for child in value.values():
            yield from _iter_image_urls(child)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_image_urls(item)


def _looks_like_image_url(value: str) -> bool:
    return value.startswith("data:image/") or re.search(r"\.(png|jpe?g|webp)(\?|$)", value, re.I) is not None


def _load_image_url(url: str) -> bytes:
    if url.startswith("data:image/"):
        _, payload = url.split(",", 1)
        return base64.b64decode(payload)
    with urllib.request.urlopen(url, timeout=300) as response:
        return response.read()
