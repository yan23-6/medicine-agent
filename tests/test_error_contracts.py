from pathlib import Path

import httpx
import pytest

from medicine_agent.bootstrap import create_facade
from medicine_agent.domain.models import SkillInvocation, SkillStatus
from medicine_agent.model_adapters.openai_compatible import (
    LlmConfig,
    OpenAICompatibleModelClient,
    load_llm_config,
)
from medicine_agent.pipeline import run_minimal_pipeline
from medicine_agent.runtime.errors import ModelCallFailedError, ModelConfigMissingError


class InvalidPayloadModel:
    provider = "test-invalid"
    model = "invalid-payload"

    def generate_json(self, *, system: str, user: str, schema: dict) -> dict:
        del system, user, schema
        return {"unexpected": True}


def test_registry_and_input_errors_are_stable() -> None:
    facade = create_facade()
    missing = facade.invoke_skill(
        SkillInvocation(task_id="missing", skill_id="not-installed", input_data={})
    )
    assert missing.status == SkillStatus.FAILURE
    assert missing.issues[0].code == "SKILL_NOT_FOUND"

    unsupported = facade.invoke_skill(
        SkillInvocation(
            task_id="version",
            skill_id="material-ingestion",
            skill_version="99.0.0",
            input_data={},
        )
    )
    assert unsupported.issues[0].code == "SKILL_VERSION_UNSUPPORTED"

    invalid = facade.invoke_skill(
        SkillInvocation(task_id="invalid", skill_id="material-ingestion", input_data={})
    )
    assert invalid.issues[0].code == "INPUT_SCHEMA_INVALID"


def test_invalid_model_payload_is_output_schema_error() -> None:
    facade = create_facade(InvalidPayloadModel())
    result = facade.invoke_skill(
        SkillInvocation(
            task_id="invalid-model",
            skill_id="knowledge-distillation",
            input_data={
                "use_model": True,
                "evidence": [
                    {
                        "evidence_id": "ev_test",
                        "source_id": "src_test",
                        "fragment_id": "frag_test",
                        "raw_text": "人工测试证据",
                        "location": {"line": 1},
                    }
                ],
            },
        )
    )
    assert result.status == SkillStatus.FAILURE
    assert result.issues[0].code == "OUTPUT_SCHEMA_INVALID"


def test_missing_live_model_config_has_stable_error(tmp_path: Path) -> None:
    with pytest.raises(ModelConfigMissingError) as raised:
        load_llm_config(tmp_path / "missing.toml")
    assert raised.value.code == "MODEL_CONFIG_MISSING"


def test_model_call_failure_does_not_expose_credentials(monkeypatch) -> None:
    class FailingClient:
        def __init__(self, *args, **kwargs) -> None:
            del args, kwargs

        def __enter__(self):
            return self

        def __exit__(self, *args) -> None:
            del args

        def post(self, url: str, json: dict):
            del url, json
            request = httpx.Request("POST", "https://example.invalid")
            raise httpx.ConnectError("offline", request=request)

    monkeypatch.setattr(httpx, "Client", FailingClient)
    client = OpenAICompatibleModelClient(
        LlmConfig(
            base_url="https://example.invalid",
            api_key="must-not-appear",
            model="test-model",
        )
    )
    with pytest.raises(ModelCallFailedError) as raised:
        client.generate_json(system="test", user="test", schema={"type": "object"})
    assert "must-not-appear" not in str(raised.value)
    assert raised.value.code == "MODEL_CALL_FAILED"


def test_broken_evidence_is_reported_and_query_is_blocked(tmp_path: Path) -> None:
    fixture = Path(__file__).parent / "fixtures" / "basic.md"
    facade = create_facade()
    result = run_minimal_pipeline(facade, input_path=fixture, output_root=tmp_path)
    package_path = Path(result["package_path"])
    (package_path / "evidence.jsonl").write_text("", encoding="utf-8")

    report = facade.validate_package(str(package_path))["report"]
    codes = {item["code"] for item in report["issues"]}
    assert report["valid"] is False
    assert "PACKAGE_CHECKSUM_MISMATCH" in codes
    assert "EVIDENCE_TRACE_BROKEN" in codes

    knowledge_id = result["query"]["matches"][0]["knowledge_id"]
    blocked = facade.invoke_skill(
        SkillInvocation(
            task_id="broken-package-query",
            skill_id="knowledge-package-query",
            input_data={
                "package_path": str(package_path),
                "knowledge_id": knowledge_id,
            },
        )
    )
    assert blocked.status == SkillStatus.FAILURE
    assert blocked.issues[0].code == "PACKAGE_VALIDATION_FAILED"
