from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from medicine_agent.domain.models import SkillManifest
from medicine_agent.runtime.base import Skill
from medicine_agent.runtime.errors import (
    SkillNotFoundError,
    SkillVersionUnsupportedError,
)


class SkillRegistry:
    def __init__(self, skills: Iterable[Skill[Any, Any]] = ()) -> None:
        self._skills: dict[tuple[str, str], Skill[Any, Any]] = {}
        for skill in skills:
            self.register(skill)

    def register(self, skill: Skill[Any, Any]) -> None:
        key = (skill.manifest.skill_id, skill.manifest.version)
        if key in self._skills:
            raise ValueError(f"Duplicate skill registration: {key}")
        self._skills[key] = skill

    def list_manifests(self) -> list[SkillManifest]:
        return sorted(
            (skill.manifest for skill in self._skills.values()),
            key=lambda item: (item.skill_id, item.version),
        )

    def resolve(self, skill_id: str, version: str | None = None) -> Skill[Any, Any]:
        versions = [
            skill
            for (registered_id, _), skill in self._skills.items()
            if registered_id == skill_id
        ]
        if not versions:
            raise SkillNotFoundError(f"Skill not found: {skill_id}")
        if version is None:
            return sorted(versions, key=lambda item: item.manifest.version)[-1]
        skill = self._skills.get((skill_id, version))
        if skill is None:
            raise SkillVersionUnsupportedError(
                f"Unsupported version {version} for skill {skill_id}"
            )
        return skill

