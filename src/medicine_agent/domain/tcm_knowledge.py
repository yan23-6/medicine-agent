"""Source-scoped TCM knowledge. Semantics are loaded from the sole registry."""
from __future__ import annotations

from typing import Literal
from pydantic import Field, JsonValue, model_validator

from medicine_agent.domain.models import StrictModel, EvidenceRecord
from medicine_agent.semantics import load_semantic_registry

KnowledgeCategory = Literal['tcm_foundation', 'chinese_materia_medica',
    'tcm_pattern_differentiation', 'tcm_formula', 'tcm_clinical_case']
GroupKind = Literal['theory', 'herb', 'differentiation', 'formula', 'case', 'dose', 'outcome', 'safety']


class EvidenceQuote(StrictModel):
    evidence_id: str = Field(min_length=1)
    text: str = Field(min_length=1)


class GroundedFact(StrictModel):
    field_id: str
    value: JsonValue = None
    state: Literal['stated', 'inferred', 'missing', 'ambiguous', 'not_applicable'] = 'stated'
    quotes: list[EvidenceQuote] = Field(default_factory=list)
    reason: str | None = None

    @model_validator(mode='after')
    def check(self):
        registry = load_semantic_registry()
        field = next((f for f in registry.fields if f.field_id == self.field_id), None)
        if field is None or field.owner_profile == 'western':
            raise ValueError('Unknown or out-of-scope medical field')
        if self.state in {'missing', 'not_applicable', 'ambiguous'}:
            if self.value is not None or not self.reason:
                raise ValueError('Missing/ambiguous facts require null value and explicit reason')
        elif self.value is None or not self.quotes:
            raise ValueError('A medical assertion requires a value and source quotes')
        if self.state == 'inferred' and not self.reason:
            raise ValueError('Inference requires an explicit rationale')
        return self


class MedicalRecordGroup(StrictModel):
    group_id: str = Field(min_length=1)
    kind: GroupKind
    # A dose can refer to its ingredient; an outcome to a visit or intervention.
    about_group_id: str | None = None
    facts: list[GroundedFact] = Field(min_length=1)

    @model_validator(mode='after')
    def check(self):
        fields = {f.field_id: f for f in load_semantic_registry().fields}
        for fact in self.facts:
            allowed = fields[fact.field_id].allowed_on
            grouped = [x.split(':', 1)[1] for x in allowed if x.startswith('tcm_group:')]
            if grouped and self.kind not in grouped:
                raise ValueError('Medical field placed in the wrong record group')
        by_id = {f.field_id: f for f in self.facts if f.state in {'stated', 'inferred'}}
        converted = by_id.get('tcm.dose_normalized_amount')
        if converted and not {'tcm.dose_unit', 'tcm.dose_conversion_basis'} <= by_id.keys():
            raise ValueError('Normalized dose requires unit and conversion basis in the same group')
        if self.kind == 'outcome' and by_id:
            required = {'tcm.outcome_evidence_context', 'tcm.outcome_outcome_kind'}
            if not required <= by_id.keys():
                raise ValueError('Outcome assertions require explicit evidence context and record kind')
            kind = by_id['tcm.outcome_outcome_kind'].value
            if kind not in {'source_claim', 'observed', 'model_prediction'}:
                raise ValueError('Unknown outcome record kind')
        return self


class AnalysisGap(StrictModel):
    reason: str = Field(min_length=1)
    quotes: list[EvidenceQuote] = Field(min_length=1)


class TCMKnowledgeNode(StrictModel):
    node_id: str = Field(min_length=1)
    source_id: str = Field(min_length=1)
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    categories: list[KnowledgeCategory] = Field(min_length=1)
    topics: list[str] = Field(default_factory=list)
    aliases: list[str] = Field(default_factory=list)
    quotes: list[EvidenceQuote] = Field(min_length=1)
    groups: list[MedicalRecordGroup] = Field(min_length=1)
    gaps: list[AnalysisGap] = Field(default_factory=list)
    review_status: Literal['unreviewed'] = 'unreviewed'
    generation_method: Literal['model'] = 'model'

    @model_validator(mode='after')
    def check_groups(self):
        ids = [g.group_id for g in self.groups]
        if len(ids) != len(set(ids)) or len(self.categories) != len(set(self.categories)):
            raise ValueError('Duplicate group identity or category')
        if any(g.about_group_id and g.about_group_id not in ids for g in self.groups):
            raise ValueError('Missing parent record group')
        parents = {g.group_id: g.about_group_id for g in self.groups}
        for start in parents:
            seen, current = set(), start
            while current is not None:
                if current in seen:
                    raise ValueError('Cyclic record group ownership')
                seen.add(current)
                current = parents[current]
        expected = {'theory': 'tcm_foundation', 'herb': 'chinese_materia_medica',
            'differentiation': 'tcm_pattern_differentiation', 'formula': 'tcm_formula',
            'case': 'tcm_clinical_case'}
        for g in self.groups:
            if g.kind in expected and expected[g.kind] not in self.categories:
                raise ValueError('Knowledge category does not cover content group')
        return self


class TCMKnowledgeGraph(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    semantic_version: Literal['0.3.0', '0.3.2'] = '0.3.2'
    analysis_status: Literal['candidate_partial'] = 'candidate_partial'
    nodes: list[TCMKnowledgeNode] = Field(default_factory=list)
    gaps: list[AnalysisGap] = Field(default_factory=list)


class KnowledgeAddress(StrictModel):
    package_id: str = Field(min_length=1)
    node_id: str = Field(min_length=1)


class KnowledgeAssociation(StrictModel):
    version: Literal['0.1.0'] = '0.1.0'
    association_id: str
    source: KnowledgeAddress
    target: KnowledgeAddress
    relation: Literal['same_definition', 'related', 'expands', 'contradicts']
    rationale: str = Field(min_length=1)
    status: Literal['candidate'] = 'candidate'
    # Addresses remain stable when folders move or a package is unplugged.
    # Neither edge direction nor same_definition creates a merged medical node.


def validate_graph_evidence(graph: TCMKnowledgeGraph, records: list[EvidenceRecord]) -> None:
    evidence = {e.evidence_id: e for e in records}
    ids = [n.node_id for n in graph.nodes]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate medical node identity')

    def check(quotes, source_id=None):
        for quote in quotes:
            record = evidence.get(quote.evidence_id)
            if record is None or quote.text not in record.raw_text:
                raise ValueError('A source quote is absent from the original evidence')
            if source_id and record.source_id != source_id:
                raise ValueError('A source node must not absorb another source')

    for gap in graph.gaps:
        check(gap.quotes)
    for node in graph.nodes:
        check(node.quotes, node.source_id)
        for group in node.groups:
            for fact in group.facts:
                check(fact.quotes, node.source_id)
        for gap in node.gaps:
            check(gap.quotes, node.source_id)


TCM_MODELS = (EvidenceQuote, GroundedFact, MedicalRecordGroup, AnalysisGap,
    TCMKnowledgeNode, TCMKnowledgeGraph, KnowledgeAddress, KnowledgeAssociation)
