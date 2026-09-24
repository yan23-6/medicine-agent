from pathlib import Path

from medicine_agent.bootstrap import create_facade
from medicine_agent.pipeline import run_minimal_pipeline


FIXTURE = Path(__file__).parent / "fixtures" / "basic.md"


def test_minimal_pipeline_round_trip_is_traceable_and_idempotent(tmp_path: Path) -> None:
    first = run_minimal_pipeline(
        create_facade(), input_path=FIXTURE, output_root=tmp_path
    )
    second = run_minimal_pipeline(
        create_facade(), input_path=FIXTURE, output_root=tmp_path
    )
    assert first["package_id"] == second["package_id"]
    assert first["quality"]["valid"] is True
    assert len(first["query"]["matches"]) == 1
    assert len(first["query"]["evidence"]) == 1
    assert Path(first["package_path"]).exists()


def test_pipeline_can_use_deterministic_model_adapter(tmp_path: Path) -> None:
    result = run_minimal_pipeline(
        create_facade(), input_path=FIXTURE, output_root=tmp_path, use_model=True
    )
    assert result["quality"]["valid"] is True
    assert result["query"]["matches"][0]["generation_method"] == "model"

