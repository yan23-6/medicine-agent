import json
from pathlib import Path

from medicine_agent.bootstrap import create_facade
from medicine_agent.contracts import export_schemas
from medicine_agent.domain.models import SkillInvocation, SkillStatus


FIXTURE = Path(__file__).parent / "fixtures" / "basic.md"
COMMITTED_SCHEMAS = Path(__file__).parents[1] / "schemas" / "t01"
COMMITTED_T02_SCHEMAS = Path(__file__).parents[1] / "schemas" / "t02"


def _ingestion_input() -> dict:
    return {
        "path": str(FIXTURE),
        "metadata": {
            "title": None,
            "author": None,
            "edition": None,
            "publication_year": None,
            "publisher": None,
            "isbn": None,
        },
    }


def test_run_records_have_unique_run_ids_and_stable_content_ids() -> None:
    facade = create_facade()
    invocation = SkillInvocation(
        task_id="repeatable-ingestion",
        skill_id="material-ingestion",
        input_data=_ingestion_input(),
    )
    first = facade.invoke_skill(invocation)
    second = facade.invoke_skill(invocation)

    assert first.status == SkillStatus.SUCCESS
    assert first.invocation_id != second.invocation_id
    assert first.input_id == second.input_id
    assert first.output_id == second.output_id
    assert facade.get_run(first.invocation_id).input_schema_id.endswith(":input")
    assert len(facade.list_runs()) == 2


def test_exported_schema_snapshot_matches_repository(tmp_path: Path) -> None:
    generated = tmp_path / "schemas"
    export_schemas(create_facade(), generated)

    expected_files = {
        path.relative_to(COMMITTED_SCHEMAS).as_posix(): path.read_bytes()
        for path in COMMITTED_SCHEMAS.rglob("*.json")
    }
    actual_files = {
        path.relative_to(generated).as_posix(): path.read_bytes()
        for path in generated.rglob("*.json")
    }
    assert actual_files == expected_files


def test_exported_t02_schema_snapshot_matches_repository(tmp_path: Path) -> None:
    generated = tmp_path / "schemas"
    export_schemas(create_facade(), generated, contract_set="t02")

    expected_files = {
        path.relative_to(COMMITTED_T02_SCHEMAS).as_posix(): path.read_bytes()
        for path in COMMITTED_T02_SCHEMAS.rglob("*.json")
    }
    actual_files = {
        path.relative_to(generated).as_posix(): path.read_bytes()
        for path in generated.rglob("*.json")
    }
    assert actual_files == expected_files


def test_registry_includes_status_and_machine_schemas() -> None:
    facade = create_facade()
    for manifest in facade.list_skills():
        assert manifest.status == "available"
        description = facade.describe_skill(manifest.skill_id, manifest.version)
        assert description["input_schema"]["type"] == "object"
        assert description["output_schema"]["type"] == "object"


def test_schema_index_has_no_machine_specific_paths() -> None:
    index = json.loads((COMMITTED_SCHEMAS / "schema-index.json").read_text("utf-8"))
    assert index["contract_set"] == "t01"
    assert all("\\" not in path and ":" not in path for path in index["files"])
