from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

from medicine_agent.domain.models import SkillManifest

InputModel = TypeVar("InputModel", bound=BaseModel)
OutputModel = TypeVar("OutputModel", bound=BaseModel)


class ModelClient(Protocol):
    provider: str
    model: str

    def generate_json(
        self, *, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]: ...


@dataclass(slots=True)
class SkillContext:
    model_client: ModelClient | None = None


class Skill(Protocol[InputModel, OutputModel]):
    manifest: SkillManifest
    input_model: type[InputModel]
    output_model: type[OutputModel]

    def execute(self, value: InputModel, context: SkillContext) -> OutputModel: ...


def manifest_path(module_file: str) -> Path:
    return Path(module_file).with_name("skill.toml")

