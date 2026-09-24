from pathlib import Path

from medicine_agent.bootstrap import create_facade
from medicine_agent.domain.models import (
    FieldMappingCandidate,
    FieldMappingStatus,
    RawFieldObservation,
    SkillInvocation,
    SkillStatus,
)


def test_unsupported_format_returns_stable_error(tmp_path: Path) -> None:
    source = tmp_path / "input.pdf"
    source.write_bytes(b"not a pdf")
    result = create_facade().invoke_skill(
        SkillInvocation(
            task_id="unsupported",
            skill_id="material-ingestion",
            input_data={
                "path": str(source),
                "metadata": {
                    "title": None,
                    "author": None,
                    "edition": None,
                    "publication_year": None,
                    "publisher": None,
                    "isbn": None,
                },
            },
        )
    )
    assert result.status == SkillStatus.FAILURE
    assert result.issues[0].code == "UNSUPPORTED_FORMAT"


def test_ambiguous_raw_field_preserves_original_value() -> None:
    item = RawFieldObservation(
        observation_id="field_1",
        source_id="source_1",
        raw_key="状态",
        raw_value={"原值": "未明确"},
        occurrence=2,
        location={"line": 10},
        context="复诊记录",
        raw_type="object",
        mapping_status=FieldMappingStatus.AMBIGUOUS,
        mapping_candidates=[
            FieldMappingCandidate(
                canonical_field="clinical_state", rationale="context candidate"
            ),
            FieldMappingCandidate(
                canonical_field="review_status", rationale="key candidate"
            ),
        ],
    )
    dumped = item.model_dump(mode="json")
    assert dumped["raw_value"] == {"原值": "未明确"}
    assert len(dumped["mapping_candidates"]) == 2

