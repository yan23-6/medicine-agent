from __future__ import annotations

import tomllib
from pathlib import Path

from medicine_agent.domain.models import SkillManifest


def load_manifest(path: Path) -> SkillManifest:
    with path.open("rb") as stream:
        payload = tomllib.load(stream)
    return SkillManifest.model_validate(payload["skill"])

