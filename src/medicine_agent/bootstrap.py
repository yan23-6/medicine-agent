from __future__ import annotations

from medicine_agent.model_adapters.fake import FakeModelClient
from medicine_agent.runtime.base import ModelClient, SkillContext
from medicine_agent.runtime.facade import ApplicationFacade
from medicine_agent.runtime.runner import SkillRunner
from medicine_agent.runtime.run_store import RunRecordStore
from medicine_agent.skills.catalog import build_registry


def create_facade(
    model_client: ModelClient | None = None,
    run_store: RunRecordStore | None = None,
) -> ApplicationFacade:
    registry = build_registry()
    context = SkillContext(model_client=model_client or FakeModelClient())
    return ApplicationFacade(
        registry=registry,
        runner=SkillRunner(registry, context, run_store=run_store),
    )

