from medicine_agent.bootstrap import create_facade


def test_registry_exposes_six_minimal_skills() -> None:
    manifests = create_facade().list_skills()
    assert {item.skill_id for item in manifests} == {
        "material-ingestion",
        "evidence-grounding",
        "knowledge-distillation",
        "knowledge-package-build-validate",
        "knowledge-package-query",
        "quality-evaluation",
    }
    for manifest in manifests:
        description = create_facade().describe_skill(manifest.skill_id)
        assert description["input_schema"]
        assert description["output_schema"]

