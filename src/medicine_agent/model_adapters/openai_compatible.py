from __future__ import annotations

import json
import os
import tomllib
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from medicine_agent.runtime.errors import ModelCallFailedError, ModelConfigMissingError


class LlmConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider: str = "openai-compatible"
    base_url: str
    api_key: str
    model: str
    timeout_seconds: int = Field(default=60, ge=1)
    max_retries: int = Field(default=2, ge=0, le=5)


def load_llm_config(path: Path) -> LlmConfig:
    if not path.exists():
        raise ModelConfigMissingError(f"LLM config not found: {path}")
    with path.open("rb") as stream:
        payload = tomllib.load(stream).get("llm", {})
    env_key = os.getenv("MEDICINE_AGENT_LLM_API_KEY")
    if env_key:
        payload["api_key"] = env_key
    config = LlmConfig.model_validate(payload)
    if not config.base_url or not config.api_key or not config.model:
        raise ModelConfigMissingError(
            "base_url, api_key and model are required for live LLM calls"
        )
    return config


class OpenAICompatibleModelClient:
    provider = "openai-compatible"

    def __init__(self, config: LlmConfig) -> None:
        self.config = config
        self.model = config.model

    def generate_json(
        self, *, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        body = {
            "model": self.config.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
        }
        try:
            with httpx.Client(
                timeout=self.config.timeout_seconds,
                headers={"Authorization": f"Bearer {self.config.api_key}"},
            ) as client:
                response = client.post(url, json=body)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                result = json.loads(content)
        except (httpx.HTTPError, KeyError, TypeError, json.JSONDecodeError) as exc:
            raise ModelCallFailedError(
                "OpenAI-compatible request failed",
                details={"provider": self.provider, "model": self.model},
            ) from exc
        if not isinstance(result, dict):
            raise ModelCallFailedError("Model response must be a JSON object")
        return result

