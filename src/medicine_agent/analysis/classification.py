"""Conservative source-text category proposals; never medical approval."""
from medicine_agent.analysis.models import PackageClassification


def classify(text: str, supplied: dict, inherited: dict | None = None) -> dict:
    value = PackageClassification.model_validate(supplied)
    declared = bool(value.subjects or value.material_types or value.knowledge_layers or value.knowledge_categories
                    or set(value.medical_profiles) - {"common"})
    if declared:
        value.status = "declared"
        value.basis = list(dict.fromkeys(value.basis + ["Caller-supplied classification"]))
    else:
        # These labels are source cues, not claims that a document has been medically reviewed.
        cues = [("textbook", ("教材", "教科书", "专著")),
                ("paper", ("摘要", "abstract", "研究方法")),
                ("physician_experience", ("医家经验", "临证经验", "医家按语")),
                ("case_record", ("主诉", "现病史", "医案"))]
        lowered = text.casefold()
        for category, words in cues:
            matches = [word for word in words if word in lowered]
            if matches:
                value.material_types.append(category)
                value.basis.append("Source cue (candidate): " + ", ".join(matches))
        if value.material_types:
            value.status = "candidate"
    if inherited:
        old = PackageClassification.model_validate(inherited)
        for field in ("subjects", "material_types", "medical_profiles", "knowledge_layers", "knowledge_categories", "basis"):
            setattr(value, field, list(dict.fromkeys(getattr(old, field) + getattr(value, field))))
        if old.status == "declared":
            value.status = "declared"
        elif old.status == "candidate" and value.status == "unclassified":
            value.status = "candidate"
    return value.model_dump(mode="json")
