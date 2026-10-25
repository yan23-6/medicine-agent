"""Synthetic contract boundaries; no session writes, sources, or model calls."""
import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from medicine_agent.domain.review_session import (
    SessionReviewer, SessionTarget, SessionOpinion, SessionSubmission,
    ReviewSessionManifest, SessionSnapshotBinding, PREPARATION_RESOURCE_NAMES,
    TargetReviewSummary, SessionEvent, SessionOpinionRecord, SessionIssue,
    ReviewSessionView, REVIEW_SESSION_MODELS,
)


def reviewer():
    return SessionReviewer(reviewer_id=' Reviewer.A ', display_name=' Synthetic A ',
        declared_role=' synthetic reviewer ')


def target(kind='source_annotation'):
    prefix = {'source_annotation': 'annotation', 'candidate': 'reviewitem', 'anomaly': 'anomaly'}[kind]
    data = dict(snapshot_id='snapshot_' + '1' * 24, kind=kind, material_id=prefix + '_' + '2' * 24)
    if kind == 'candidate':
        data['review_target'] = dict(address={'package_id': 'pkg', 'node_id': 'node'},
            scope='node', fingerprint='a' * 64)
    return SessionTarget(**data)


def opinion(kind='source_annotation', **kwargs):
    return SessionOpinion(target=target(kind), decision='revise', reason=' Synthetic reason ', **kwargs)


def binding():
    return SessionSnapshotBinding(snapshot_id='snapshot_' + '1' * 24,
        preparation_id='preparation_' + '2' * 24, manifest_sha256='a' * 64,
        snapshot_files={name: 'a' * 64 for name in PREPARATION_RESOURCE_NAMES},
        source_archives={'synthetic.medpkg': 'b' * 64})


def test_declared_identity_normalized_without_certification():
    r = reviewer()
    assert r.reviewer_id == 'reviewer.a' and r.display_name == 'Synthetic A'
    assert r.identity_status == 'self_declared'


def test_distinct_material_kinds_cannot_be_cast_to_review_targets():
    candidate = target('candidate')
    assert candidate.review_target is not None
    for kind in ('source_annotation', 'anomaly'):
        data = target(kind).model_dump()
        data['review_target'] = candidate.review_target
        with pytest.raises(ValidationError):
            SessionTarget.model_validate(data)


def test_correction_candidates_respect_source_and_anomaly_boundaries():
    assert opinion(proposed_value='Synthetic correction').proposed_value == 'Synthetic correction'
    with pytest.raises(ValidationError):
        opinion(proposed_value={'value': 'Not original text'})
    with pytest.raises(ValidationError):
        opinion('anomaly', proposed_value='Not a writable target')


def test_one_batch_cannot_create_two_independent_votes_for_same_target():
    with pytest.raises(ValidationError):
        SessionSubmission(session_id='reviewsession_' + '3' * 24, submission_id='synthetic-1',
            reviewer=reviewer(), opinions=[opinion(), opinion()])


@pytest.mark.parametrize('created', [datetime(2026, 1, 1),
    datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=8)))])
def test_manifest_requires_explicit_utc_and_never_medical_confirmation(created):
    with pytest.raises(ValidationError):
        ReviewSessionManifest(session_id='reviewsession_' + '3' * 24,
            created_at=created, binding=binding())
    manifest = ReviewSessionManifest(session_id='reviewsession_' + '3' * 24,
        created_at=datetime(2026, 1, 1, tzinfo=UTC), binding=binding())
    assert manifest.medical_review == 'unreviewed' and manifest.release_allowed is False


def test_disagreement_cannot_be_silently_marked_adjudicated():
    with pytest.raises(ValidationError):
        TargetReviewSummary(target=target(), agreement_state='disagreement',
            adjudication_state='not_required', latest_opinion_ids=[], unable_to_judge_count=0)


# --- D03 fixed model matrix (appended 2026-10-24; tests above unchanged) ---
# Structural checks only: no source lookup, no content IDs, no history chain.

def target_of(kind='source_annotation', snapshot='1' * 24, suffix='2' * 24):
    prefix = {'source_annotation': 'annotation', 'candidate': 'reviewitem', 'anomaly': 'anomaly'}[kind]
    data = dict(snapshot_id='snapshot_' + snapshot, kind=kind, material_id=prefix + '_' + suffix)
    if kind == 'candidate':
        data['review_target'] = dict(address={'package_id': 'pkg', 'node_id': 'node'},
            scope='node', fingerprint='a' * 64)
    return SessionTarget(**data)


def opinion_of(kind='source_annotation', decision='revise', reason='Synthetic reason', **kwargs):
    return SessionOpinion(target=target_of(kind), decision=decision, reason=reason, **kwargs)


def binding_data():
    return dict(snapshot_id='snapshot_' + '1' * 24, preparation_id='preparation_' + '2' * 24,
        manifest_sha256='a' * 64,
        snapshot_files={name: 'a' * 64 for name in PREPARATION_RESOURCE_NAMES},
        source_archives={'synthetic.medpkg': 'b' * 64})


def manifest_of(**kwargs):
    data = dict(session_id='reviewsession_' + '3' * 24, created_at=datetime(2026, 1, 1, tzinfo=UTC),
        binding=binding())
    data.update(kwargs)
    return ReviewSessionManifest(**data)


def submission_of(**kwargs):
    data = dict(session_id='reviewsession_' + '3' * 24, submission_id='synthetic-1',
        reviewer=reviewer(), opinions=[opinion_of()])
    data.update(kwargs)
    return SessionSubmission(**data)


def event_of(**kwargs):
    data = dict(event_id='sessionevent_' + '5' * 24, created_at=datetime(2026, 1, 1, tzinfo=UTC),
        submission=submission_of())
    data.update(kwargs)
    return SessionEvent(**data)


def record_of(**kwargs):
    data = dict(opinion_id='sessionopinion_' + '4' * 24, event_id='sessionevent_' + '5' * 24,
        opinion_index=0, created_at=datetime(2026, 1, 1, tzinfo=UTC), reviewer=reviewer(),
        opinion=opinion_of())
    data.update(kwargs)
    return SessionOpinionRecord(**data)


def summary_of(**kwargs):
    data = dict(target=target(), agreement_state='pending', adjudication_state='not_required',
        latest_opinion_ids=[], unable_to_judge_count=0)
    data.update(kwargs)
    return TargetReviewSummary(**data)


def view_of(**kwargs):
    data = dict(version='0.1.0', manifest=manifest_of(), opinions=[], targets=[],
        issues=[], writable=True)
    data.update(kwargs)
    return ReviewSessionView(**data)


def valid_samples():
    """One valid synthetic value per frozen model, for the unknown-field sweep."""
    return {
        SessionSnapshotBinding: binding(),
        SessionReviewer: reviewer(),
        SessionTarget: target_of(),
        SessionOpinion: opinion_of(),
        SessionSubmission: submission_of(),
        ReviewSessionManifest: manifest_of(),
        SessionEvent: event_of(),
        SessionOpinionRecord: record_of(),
        SessionIssue: SessionIssue(code='SYNTHETIC_ISSUE'),
        TargetReviewSummary: summary_of(),
        ReviewSessionView: view_of(),
    }


# Row 1: declared identity is normalized and never authenticated.
@pytest.mark.parametrize('value', ['', '   ', 'a/b', 'a\\b', 'a:b', 'A' * 129, '-leading'])
def test_reviewer_id_rejects_invalid_values(value):
    with pytest.raises(ValidationError):
        SessionReviewer(reviewer_id=value, display_name='Synthetic', declared_role='synthetic')


def test_reviewer_id_normalization_cannot_create_a_second_voter():
    legacy = SessionReviewer(reviewer_id=' Reviewer.A ', display_name='A', declared_role='r')
    normalized = SessionReviewer(reviewer_id='reviewer.a', display_name='A', declared_role='r')
    assert legacy.reviewer_id == normalized.reviewer_id == 'reviewer.a'
    assert len({legacy.reviewer_id, normalized.reviewer_id}) == 1


@pytest.mark.parametrize('field', ['display_name', 'declared_role'])
def test_reviewer_display_and_role_must_be_nonblank(field):
    data = dict(reviewer_id='reviewer.a', display_name='Synthetic', declared_role='synthetic')
    data[field] = '   '
    with pytest.raises(ValidationError):
        SessionReviewer(**data)


def test_reviewer_identity_status_cannot_be_authenticated():
    with pytest.raises(ValidationError):
        SessionReviewer(reviewer_id='reviewer.a', display_name='Synthetic',
            declared_role='synthetic', identity_status='authenticated')


# Row 2: material kinds keep their own identity prefix and optional target.
@pytest.mark.parametrize('kind,material_id', [
    ('source_annotation', 'reviewitem_' + '2' * 24),
    ('candidate', 'annotation_' + '2' * 24),
    ('anomaly', 'anomaly_' + 'A' * 24),
    ('anomaly', 'anomaly_' + '2' * 23),
    ('anomaly', 'anomaly_' + 'g' * 24),
])
def test_material_identity_matches_kind(kind, material_id):
    with pytest.raises(ValidationError):
        SessionTarget(snapshot_id='snapshot_' + '1' * 24, kind=kind, material_id=material_id)


def test_candidate_requires_review_target_and_others_forbid_it():
    with pytest.raises(ValidationError):
        SessionTarget(snapshot_id='snapshot_' + '1' * 24, kind='candidate',
            material_id='reviewitem_' + '2' * 24)
    for kind in ('source_annotation', 'anomaly'):
        with pytest.raises(ValidationError):
            SessionTarget(snapshot_id='snapshot_' + '1' * 24, kind=kind,
                material_id={'source_annotation': 'annotation_', 'anomaly': 'anomaly_'}[kind] + '2' * 24,
                review_target=target_of('candidate').review_target)


def test_three_material_kinds_round_trip():
    for kind in ('source_annotation', 'candidate', 'anomaly'):
        value = target_of(kind)
        assert SessionTarget.model_validate(value.model_dump()) == value


# Row 3: all four decisions need a reason; unable_to_judge never becomes accept.
@pytest.mark.parametrize('decision', ['accept', 'revise', 'reject', 'unable_to_judge'])
def test_four_decisions_with_reason_are_kept(decision):
    value = opinion_of(decision=decision)
    assert value.decision == decision
    assert SessionOpinion.model_validate(value.model_dump()).decision == decision


@pytest.mark.parametrize('kwargs', [dict(decision='approve'),
                                    dict(decision='accept', reason='   '),
                                    dict(decision='accept', reason='x' * 8001)])
def test_unknown_decision_and_bad_reason_rejected(kwargs):
    with pytest.raises(ValidationError):
        opinion_of(**kwargs)


# Row 4: correction candidates stay inside revise and inside their own material kind.
@pytest.mark.parametrize('decision', ['accept', 'reject', 'unable_to_judge'])
@pytest.mark.parametrize('kind', ['source_annotation', 'candidate'])
def test_non_revise_decision_cannot_carry_proposed_value(decision, kind):
    with pytest.raises(ValidationError):
        opinion_of(kind=kind, decision=decision, proposed_value='Synthetic value')


def test_anomaly_cannot_carry_proposed_value():
    with pytest.raises(ValidationError):
        opinion_of('anomaly', proposed_value={'value': 'not writable'})


@pytest.mark.parametrize('value', ['', '   ', {'value': 'object'}])
def test_source_correction_must_be_nonblank_text(value):
    with pytest.raises(ValidationError):
        opinion_of(proposed_value=value)


def test_revision_values_round_trip_and_may_be_absent():
    source = opinion_of(proposed_value='Synthetic correction')
    assert source.proposed_value == 'Synthetic correction'
    candidate = opinion_of('candidate', proposed_value={'value': 'Synthetic'})
    assert candidate.proposed_value == {'value': 'Synthetic'}
    assert opinion_of().proposed_value is None


# Row 5: previous-opinion addressing and record index are strict.
def test_expected_previous_id_must_be_an_opinion_id():
    with pytest.raises(ValidationError):
        opinion_of(expected_previous_id='opinion_' + '4' * 24)
    value = opinion_of(expected_previous_id='sessionopinion_' + '4' * 24)
    assert value.expected_previous_id == 'sessionopinion_' + '4' * 24


@pytest.mark.parametrize('index', [-1, True, '0', 1.5])
def test_opinion_index_rejects_non_integer(index):
    with pytest.raises(ValidationError):
        record_of(opinion_index=index)


def test_opinion_index_zero_accepted():
    assert record_of(opinion_index=0).opinion_index == 0


# Row 6: batch submission boundaries.
@pytest.mark.parametrize('submission_id', ['', ' a/b ', 'A' * 129, '-leading'])
def test_submission_id_rejects_invalid_values(submission_id):
    with pytest.raises(ValidationError):
        submission_of(submission_id=submission_id)


def test_submission_opinion_list_bounds():
    with pytest.raises(ValidationError):
        submission_of(opinions=[])
    with pytest.raises(ValidationError):
        submission_of(opinions=[opinion_of() for _ in range(1001)])


@pytest.mark.parametrize('opinions', [
    lambda: [opinion_of(), opinion_of()],
    lambda: [opinion_of(), SessionOpinion(target=target_of('anomaly', snapshot='9' * 24),
        decision='accept', reason='Synthetic reason')],
])
def test_batch_rejects_duplicate_material_or_two_snapshots(opinions):
    with pytest.raises(ValidationError):
        submission_of(opinions=opinions())


def test_batch_accepts_distinct_materials_of_one_snapshot():
    value = submission_of(opinions=[opinion_of(),
        SessionOpinion(target=target_of(suffix='7' * 24), decision='accept', reason='Synthetic')])
    assert len(value.opinions) == 2


# Row 7: snapshot binding covers exactly seven files and package filenames only.
@pytest.mark.parametrize('change', ['missing', 'extra', 'wrong_name', 'manifest_mismatch'])
def test_binding_resource_set_is_exact(change):
    data = binding_data()
    if change == 'missing':
        data['snapshot_files'].pop('README.md')
    elif change == 'extra':
        data['snapshot_files']['synthetic.md'] = 'a' * 64
    elif change == 'wrong_name':
        data['snapshot_files']['readme.md'] = data['snapshot_files'].pop('README.md')
    else:
        data['snapshot_files']['manifest.json'] = 'b' * 64
    with pytest.raises(ValidationError):
        SessionSnapshotBinding(**data)


@pytest.mark.parametrize('archives', [{}, {'dir/pkg.medpkg': 'b' * 64}, {'notes.txt': 'b' * 64},
                                      {'../pkg.medpkg': 'b' * 64}])
def test_source_archives_must_be_plain_medpkg_names(archives):
    data = binding_data()
    data['source_archives'] = archives
    with pytest.raises(ValidationError):
        SessionSnapshotBinding(**data)


def test_binding_round_trips_without_touching_files():
    value = binding()
    assert SessionSnapshotBinding.model_validate(value.model_dump()) == value
    assert len(value.snapshot_files) == 7 and set(value.source_archives) == {'synthetic.medpkg'}


# Row 8: explicit UTC only; records are derived projections.
@pytest.mark.parametrize('created', [datetime(2026, 1, 1),
                                     datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=8)))])
def test_event_and_record_require_utc(created):
    with pytest.raises(ValidationError):
        event_of(created_at=created)
    with pytest.raises(ValidationError):
        record_of(created_at=created)


def test_utc_timestamps_round_trip_through_json():
    event = event_of()
    restored = SessionEvent.model_validate_json(event.model_dump_json())
    assert restored.created_at == event.created_at


def test_opinion_record_is_a_derived_projection():
    record = record_of()
    fields = set(type(record).model_fields)
    assert fields == {'opinion_id', 'event_id', 'opinion_index',
        'created_at', 'reviewer', 'opinion'}
    assert 'version' not in fields


# Row 9: medical and release boundaries are fixed literals.
@pytest.mark.parametrize('field,value', [('medical_review', 'confirmed'),
                                         ('release_allowed', True),
                                         ('reviewer_identity', 'authenticated')])
def test_manifest_medical_boundaries_are_fixed(field, value):
    with pytest.raises(ValidationError):
        manifest_of(**{field: value})


@pytest.mark.parametrize('field,value', [('medical_review', 'confirmed'),
                                         ('release_allowed', True),
                                         ('reviewer_identity', 'authenticated')])
def test_view_medical_boundaries_are_fixed(field, value):
    with pytest.raises(ValidationError):
        view_of(**{field: value})


def test_manifest_defaults_stay_unreviewed():
    value = manifest_of()
    assert (value.medical_review, value.release_allowed, value.reviewer_identity) == (
        'unreviewed', False, 'self_declared')


# Row 10: summaries keep disagreements pending adjudication.
def test_agreement_cannot_be_marked_awaiting_adjudication():
    with pytest.raises(ValidationError):
        summary_of(agreement_state='agreement', adjudication_state='awaiting_adjudication')


def test_summary_rejects_duplicate_and_bad_counts():
    with pytest.raises(ValidationError):
        summary_of(agreement_state='agreement', adjudication_state='not_required',
            latest_opinion_ids=['sessionopinion_' + '4' * 24] * 2)
    for count in (-1, True):
        with pytest.raises(ValidationError):
            summary_of(unable_to_judge_count=count)


def test_disagreement_stays_awaiting_adjudication():
    value = summary_of(agreement_state='disagreement', adjudication_state='awaiting_adjudication')
    assert value.adjudication_state == 'awaiting_adjudication'


# Row 11: an invalid session history view is read-only.
@pytest.mark.parametrize('kwargs', [
    dict(issues=[SessionIssue(code='SYNTHETIC_HISTORY_INVALID')]),
    dict(targets=[summary_of(history_invalid=True)]),
])
def test_invalid_history_view_cannot_be_writable(kwargs):
    with pytest.raises(ValidationError):
        view_of(writable=True, **kwargs)
    assert view_of(writable=False, **kwargs).writable is False


def test_clean_view_can_be_writable():
    assert view_of(writable=True).writable is True


# Row 12: unknown fields and versions are rejected; version defaults in Python.
@pytest.mark.parametrize('model,value', list(valid_samples().items()))
def test_unknown_field_rejected(model, value):
    data = value.model_dump(mode='json')
    data['synthetic_unknown_field'] = 1
    with pytest.raises(ValidationError):
        model.model_validate(data)


@pytest.mark.parametrize('factory', [manifest_of, event_of, submission_of, view_of])
def test_explicit_unknown_version_rejected(factory):
    with pytest.raises(ValidationError):
        factory(version='0.2.0')


def test_python_construction_defaults_version():
    assert submission_of().version == '0.1.0'
    assert manifest_of().version == '0.1.0'
    assert event_of().version == '0.1.0'
    assert view_of().version == '0.1.0'


def test_frozen_model_tuple_has_eleven_entries():
    assert len(REVIEW_SESSION_MODELS) == 11
    assert [m.__name__ for m in REVIEW_SESSION_MODELS] == [
        'SessionSnapshotBinding', 'SessionReviewer', 'SessionTarget', 'SessionOpinion',
        'SessionSubmission', 'ReviewSessionManifest', 'SessionEvent', 'SessionOpinionRecord',
        'SessionIssue', 'TargetReviewSummary', 'ReviewSessionView']


# Row 13: API export matches the committed snapshot byte for byte.
def test_api_export_matches_repository_snapshot(tmp_path):
    from medicine_agent.bootstrap import create_facade
    from medicine_agent.contracts import export_schemas

    index = export_schemas(create_facade(), tmp_path, contract_set='review-session')
    assert index['contract_set'] == 'review-session' and index['contract_version'] == '0.1.0'
    assert len(index['files']) == 11 and not (tmp_path / 'skills').exists()
    exported = {p.relative_to(tmp_path).as_posix(): p.read_bytes()
                for p in tmp_path.rglob('*') if p.is_file()}
    repository = {p.relative_to(Path('schemas/review-session')).as_posix(): p.read_bytes()
                  for p in Path('schemas/review-session').rglob('*') if p.is_file()}
    assert exported == repository


# Row 14: existing CLI option and all earlier contract sets stay byte-identical.
LEGACY_CONTRACTS = ['t01', 't02', 't02p', 'tcm', 'review', 'correction',
                    'owned-analysis', 'learning', 'coverage', 'review-preparation']


def test_cli_export_and_legacy_contract_sets_unchanged(tmp_path):
    from medicine_agent.bootstrap import create_facade
    from medicine_agent.contracts import export_schemas

    cli_dir = tmp_path / 'cli-session'
    result = subprocess.run([sys.executable, '-m', 'medicine_agent.cli', 'export-schemas',
        '--contract-set', 'review-session', '--output-dir', str(cli_dir)],
        capture_output=True, encoding='utf-8')
    assert result.returncode == 0, result.stdout + result.stderr

    facade = create_facade()
    api_dir = tmp_path / 'api-session'
    export_schemas(facade, api_dir, contract_set='review-session')
    as_bytes = lambda root: {p.relative_to(root).as_posix(): p.read_bytes()
                             for p in root.rglob('*') if p.is_file()}
    assert as_bytes(cli_dir) == as_bytes(api_dir)

    for contract in LEGACY_CONTRACTS:
        out = tmp_path / ('legacy-' + contract)
        export_schemas(facade, out, contract_set=contract)
        assert as_bytes(out) == as_bytes(Path('schemas') / contract), contract
