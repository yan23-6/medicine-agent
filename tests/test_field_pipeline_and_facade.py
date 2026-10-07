import json
from pathlib import Path

from medicine_agent.bootstrap import create_facade
from medicine_agent.packages.io import read_jsonl
from medicine_agent.pipeline import run_minimal_pipeline


FIXTURE = Path(__file__).parent / "fixtures" / "basic.md"
RAW_FIELDS = Path(__file__).parent / "fixtures" / "ambiguous_fields.json"


def test_ambiguous_fields_and_multi_evidence_complete_round_trip(
    tmp_path: Path,
) -> None:
    facade = create_facade()
    raw_fields = json.loads(RAW_FIELDS.read_text(encoding="utf-8"))
    result = run_minimal_pipeline(
        facade,
        input_path=FIXTURE,
        output_root=tmp_path,
        raw_fields=raw_fields,
        combine_evidence=True,
    )

    package_path = Path(result["package_path"])
    stored_fields = read_jsonl(package_path / "raw_fields.jsonl")
    assert len(stored_fields) == len(raw_fields)
    assert [item["occurrence"] for item in stored_fields if item["raw_key"] == "状态"] == [
        1,
        2,
    ]
    assert [item["occurrence"] for item in stored_fields if item["raw_key"] == "舌象"] == [
        1,
        2,
    ]
    assert any(item["mapping_status"] == "ambiguous" for item in stored_fields)
    assert any(item["mapping_status"] == "unmapped" for item in stored_fields)
    assert any(item["raw_value"] == {"原值": "不可确定"} for item in stored_fields)

    assert result["quality"]["valid"] is True
    issue_codes = {item["code"] for item in result["quality"]["issues"]}
    assert "AMBIGUOUS_FIELD_MAPPING" in issue_codes
    assert "UNMAPPED_FIELD_PRESERVED" in issue_codes
    assert len(result["query"]["matches"]) == 1
    assert len(result["query"]["evidence"]) == 3
    assert len(read_jsonl(package_path / "runs.jsonl")) == 3

    validation = facade.validate_package(str(package_path))
    assert validation["report"]["valid"] is True
    knowledge_id = result["query"]["matches"][0]["knowledge_id"]
    queried = facade.query_package(str(package_path), knowledge_id=knowledge_id)
    traced = facade.trace_evidence(str(package_path), knowledge_id)
    assert len(queried["evidence"]) == 3
    assert traced["evidence"] == queried["evidence"]
