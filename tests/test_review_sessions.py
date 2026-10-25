"""Independent session software tests using self-authored package fixtures."""
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from medicine_agent.analysis import review_sessions as sessions_module
from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.review_sessions import ReviewSessionService
from medicine_agent.domain.ids import content_hash, stable_id
from medicine_agent.domain.review_session import (
    SessionEvent, SessionOpinion, SessionReviewer, SessionSubmission,
)
from test_review_snapshot import exported, material, snapshot


@pytest.fixture
def session(exported, tmp_path):
    preparation, packages, workspace = exported
    service = ReviewSessionService(packages, workspace)
    root = tmp_path / 'session'
    manifest = service.create(preparation, root)
    target = next(t.target for t in service.inspect(root).targets if t.target.kind == 'candidate')
    return service, root, manifest, target


def request(session, *, reviewer='reviewer-a', submission='synthetic-1', decision='accept', previous=None):
    _, _, manifest, target = session
    return dict(version='0.1.0', session_id=manifest.session_id, submission_id=submission,
        reviewer=dict(reviewer_id=reviewer, display_name='Synthetic reviewer', declared_role='software test'),
        opinions=[dict(target=target.model_dump(mode='json'), decision=decision,
            reason='Self authored software opinion, not a medical conclusion', expected_previous_id=previous)])


def test_independent_votes_retry_and_unable_do_not_confirm_medicine(session):
    service, root, _, target = session
    first = service.submit(root, request(session))
    assert service.submit(root, request(session)).event_id == first.event_id
    service.submit(root, request(session, reviewer='reviewer-b', submission='synthetic-2', decision='reject'))
    service.submit(root, request(session, reviewer='reviewer-c', submission='synthetic-3', decision='unable_to_judge'))
    view = service.inspect(root)
    row = next(t for t in view.targets if t.target == target)
    assert row.agreement_state == 'disagreement' and row.adjudication_state == 'awaiting_adjudication'
    assert row.unable_to_judge_count == 1 and len(view.opinions) == 3
    assert view.writable and view.medical_review == 'unreviewed' and not view.release_allowed


def test_normalized_reviewer_updates_one_chain_and_stale_batch_writes_nothing(session):
    service, root, _, target = session
    service.submit(root, request(session))
    view = service.inspect(root)
    previous = view.opinions[0].opinion_id
    service.submit(root, request(session, reviewer=' Reviewer-A ', submission='synthetic-2', previous=previous))
    view = service.inspect(root)
    row = next(t for t in view.targets if t.target == target)
    assert row.agreement_state == 'insufficient_opinions' and len(row.latest_opinion_ids) == 1
    before = snapshot(root / 'events')
    batch = request(session, submission='synthetic-3')  # The old head is stale.
    other = next(t.target for t in view.targets if t.target != target)
    batch['opinions'].insert(0, dict(target=other.model_dump(mode='json'), decision='accept', reason='Synthetic'))
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, batch)
    assert exc.value.code == 'SESSION_STALE_WRITE'
    assert snapshot(root / 'events') == before


def test_corrupt_event_is_auditable_and_blocks_writes(session):
    service, root, _, _ = session
    event = service.submit(root, request(session))
    path = root / 'events' / (event.event_id + '.json')
    data = json.loads(path.read_text('utf-8'))
    data['event']['submission']['opinions'][0]['reason'] = 'Synthetic tamper'
    path.write_text(json.dumps(data), encoding='utf-8')
    view = service.inspect(root)
    assert not view.writable and view.issues[0].code == 'SESSION_EVENT_INVALID'
    before = snapshot(root / 'events')
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, request(session, submission='synthetic-2'))
    assert exc.value.code == 'SESSION_HISTORY_INVALID'
    assert snapshot(root / 'events') == before


def test_create_and_submit_never_change_source_packages_or_preparation(exported, tmp_path):
    preparation, packages, workspace = exported
    before = snapshot(preparation), snapshot(packages)
    service = ReviewSessionService(packages, workspace)
    root = tmp_path / 'session'
    manifest = service.create(preparation, root)
    view = service.inspect(root)
    target = next(t.target for t in view.targets if t.target.kind == 'source_annotation')
    service.submit(root, request((service, root, manifest, target)))
    assert (snapshot(preparation), snapshot(packages)) == before
    with pytest.raises(AnalysisError) as exc:
        service.create(preparation, root)
    assert exc.value.code == 'SESSION_EXISTS'


# --- D04 fixed runtime matrix (appended 2026-10-24; tests above unchanged) ---

def targets_of(service, root):
    return {t.target.kind: t.target for t in service.inspect(root).targets}


def batch(session, *entries, submission='synthetic-batch', reviewer='reviewer-a'):
    """entries: (target, decision, previous) triples in one snapshot."""
    _, _, manifest, _ = session
    return dict(version='0.1.0', session_id=manifest.session_id, submission_id=submission,
        reviewer=dict(reviewer_id=reviewer, display_name='Synthetic reviewer',
                      declared_role='software test'),
        opinions=[dict(target=t.model_dump(mode='json'), decision=d,
                       reason='Self authored software opinion', expected_previous_id=p)
                  for t, d, p in entries])


def build_event(manifest, target, *, reviewer='reviewer-a', decision='accept',
                submission='synthetic-x', session_id=None, previous=None, moment=None):
    event = SessionEvent(event_id='sessionevent_' + '0' * 24,
        created_at=moment or datetime.now(UTC),
        submission=SessionSubmission(session_id=session_id or manifest.session_id,
            submission_id=submission,
            reviewer=SessionReviewer(reviewer_id=reviewer, display_name='Synthetic reviewer',
                declared_role='software test'),
            opinions=[SessionOpinion(target=target, decision=decision,
                reason='Self authored software opinion', expected_previous_id=previous)]))
    event.event_id = stable_id('sessionevent', event.model_dump(mode='json', exclude={'event_id'}))
    return event


def event_wrapper(event):
    payload = event.model_dump(mode='json')
    return {'event': payload, 'sha256': content_hash(payload)}


def write_event(root, event, wrapper=None):
    path = root / 'events' / (event.event_id + '.json')
    path.write_text(json.dumps(wrapper if wrapper is not None else event_wrapper(event)),
                    encoding='utf-8')
    return path


def opinion_id(event):
    return stable_id('sessionopinion', {'event_id': event.event_id, 'opinion_index': 0})


def manifest_sidecar(root):
    return json.loads((root / 'session.json').read_text('utf-8'))


def put_sidecar(root, data, resign=True):
    if resign:
        data['manifest']['session_id'] = stable_id('reviewsession',
            {k: v for k, v in data['manifest'].items() if k != 'session_id'})
        data['sha256'] = content_hash(data['manifest'])
    (root / 'session.json').write_text(json.dumps(data), encoding='utf-8')


# Row 1: create never overwrites and never nests inside protected paths.
@pytest.mark.parametrize('case,code', [
    ('existing_dir', 'SESSION_EXISTS'), ('existing_file', 'SESSION_EXISTS'),
    ('in_packages', 'SESSION_PATH_INVALID'), ('in_workspace', 'SESSION_PATH_INVALID'),
    ('same_as_preparation', 'SESSION_PATH_INVALID'),
])
def test_create_rejects_existing_or_nested_target(exported, tmp_path, case, code):
    preparation, packages, workspace = exported
    service = ReviewSessionService(packages, workspace)
    if case == 'existing_dir':
        target = tmp_path / 'session'
        target.mkdir()
        sentinel = None
    elif case == 'existing_file':
        target = tmp_path / 'session'
        target.write_text('synthetic placeholder', encoding='utf-8')
        sentinel = target.read_bytes()
    elif case == 'in_packages':
        target, sentinel = packages / 'nested-session', None
    elif case == 'in_workspace':
        target, sentinel = workspace / 'nested-session', None
    else:
        target, sentinel = preparation, None
    before = snapshot(preparation), snapshot(packages)
    with pytest.raises(AnalysisError) as exc:
        service.create(preparation, target)
    assert exc.value.code == code
    assert (snapshot(preparation), snapshot(packages)) == before
    if sentinel is not None:
        assert target.read_bytes() == sentinel


# Row 2: session.json corruption is rejected with a fixed message.
@pytest.mark.parametrize('damage', ['sha_mismatch', 'missing_version', 'unknown_version',
                                    'duplicate_key', 'unknown_wrapper_key', 'forged_session_id',
                                    'marker_in_field'])
def test_session_manifest_corruption_rejected(session, damage):
    service, root, manifest, _ = session
    path = root / 'session.json'
    marker = 'SENTINEL_MANIFEST_7c1'
    text = path.read_text('utf-8')
    data = json.loads(text)
    if damage == 'sha_mismatch':
        data['manifest']['session_id'] = 'reviewsession_' + '9' * 24
        path.write_text(json.dumps(data), encoding='utf-8')
    elif damage in {'missing_version', 'unknown_version'}:
        if damage == 'missing_version':
            data['manifest'].pop('version', None)
        else:
            data['manifest']['version'] = '0.2.0'
        put_sidecar(root, data)
    elif damage == 'unknown_wrapper_key':
        data['synthetic_extra'] = 1
        path.write_text(json.dumps(data), encoding='utf-8')
    elif damage == 'forged_session_id':
        data['manifest']['session_id'] = 'reviewsession_' + '9' * 24
        data['sha256'] = content_hash(data['manifest'])
        path.write_text(json.dumps(data), encoding='utf-8')
    elif damage == 'marker_in_field':
        data['manifest']['binding']['preparation_id'] = marker
        put_sidecar(root, data)
    else:
        body = text.strip()
        assert body.endswith('}')
        path.write_text(body[:-1] + ', "manifest": {}, "manifest": {}}', encoding='utf-8')
    with pytest.raises(AnalysisError) as exc:
        service.inspect(root)
    assert exc.value.code == 'SESSION_MANIFEST_INVALID'
    assert marker not in str(exc.value)


# Row 3: a re-signed manifest still cannot rebind a different snapshot.
@pytest.mark.parametrize('field', ['source_archives', 'preparation_id', 'snapshot_id'])
def test_resigned_binding_mismatch_rejected(session, field):
    service, root, _, _ = session
    data = manifest_sidecar(root)
    binding = data['manifest']['binding']
    if field == 'source_archives':
        binding['source_archives'] = {'synthetic.medpkg': 'c' * 64}
    elif field == 'preparation_id':
        binding['preparation_id'] = 'preparation_' + '7' * 24
    else:
        binding['snapshot_id'] = 'snapshot_' + '7' * 24
    put_sidecar(root, data)
    with pytest.raises(AnalysisError) as exc:
        service.inspect(root)
    assert exc.value.code == 'SESSION_SNAPSHOT_INVALID'


def test_copied_snapshot_body_change_rejected(session):
    service, root, _, _ = session
    path = root / 'preparation' / 'candidates.md'
    path.write_bytes(path.read_bytes() + b' ')
    with pytest.raises(AnalysisError) as exc:
        service.inspect(root)
    assert exc.value.code == 'SESSION_SNAPSHOT_INVALID'


# Row 4: all three material kinds are writable targets; foreign targets are not.
def test_three_material_kinds_submit_and_invalid_targets_rejected(session, exported):
    service, root, manifest, _ = session
    targets = targets_of(service, root)
    before = snapshot(exported[0]), snapshot(exported[1])
    events = [service.submit(root, batch(session, (targets[kind], 'accept', None),
        submission='synthetic-kind-' + kind)) for kind in
        ('source_annotation', 'candidate', 'anomaly')]
    assert len({e.event_id for e in events}) == 3

    candidate = targets['candidate']
    unknown = candidate.model_copy(update={'material_id': 'reviewitem_' + 'f' * 24})
    wrong_snapshot = candidate.model_copy(update={'snapshot_id': 'snapshot_' + '9' * 24})
    forged_target = candidate.model_copy(update={'review_target': candidate.review_target.model_copy(
        update={'fingerprint': 'b' * 64})})
    for invalid in (unknown, wrong_snapshot, forged_target):
        with pytest.raises(AnalysisError) as exc:
            service.submit(root, batch(session, (invalid, 'accept', None),
                submission='synthetic-invalid-' + invalid.material_id[-4:]))
        assert exc.value.code == 'SESSION_TARGET_INVALID'
    assert (snapshot(exported[0]), snapshot(exported[1])) == before


# Row 5: one bad entry rejects the whole batch.
def test_batch_with_bad_target_writes_nothing(session):
    service, root, manifest, _ = session
    targets = targets_of(service, root)
    unknown = targets['candidate'].model_copy(update={'material_id': 'reviewitem_' + 'f' * 24})
    before = snapshot(root / 'events')
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, batch(session, (targets['source_annotation'], 'accept', None),
            (unknown, 'accept', None), submission='synthetic-mixed'))
    assert exc.value.code == 'SESSION_TARGET_INVALID'
    assert snapshot(root / 'events') == before


def test_batch_with_stale_previous_writes_nothing(session):
    service, root, manifest, _ = session
    targets = targets_of(service, root)
    first = service.submit(root, batch(session, (targets['source_annotation'], 'accept', None)))
    before = snapshot(root / 'events')
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, batch(session, (targets['candidate'], 'accept', None),
            (targets['source_annotation'], 'accept', 'sessionopinion_' + 'f' * 24),
            submission='synthetic-stale-batch'))
    assert exc.value.code == 'SESSION_STALE_WRITE'
    assert snapshot(root / 'events') == before


# Row 6: agreement, disagreement, pending and unable counting.
def test_two_declared_ids_same_decision_agree_without_medical_confirmation(session):
    service, root, manifest, target = session
    service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-b',
        reviewer='reviewer-b'))
    view = service.inspect(root)
    row = next(t for t in view.targets if t.target == target)
    assert row.agreement_state == 'agreement' and row.adjudication_state == 'not_required'
    assert view.medical_review == 'unreviewed' and view.release_allowed is False


def test_accept_reject_disagreement_stays_awaiting(session):
    service, root, manifest, target = session
    service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    service.submit(root, batch(session, (target, 'reject', None), submission='synthetic-b',
        reviewer='reviewer-b'))
    row = next(t for t in service.inspect(root).targets if t.target == target)
    assert row.agreement_state == 'disagreement'
    assert row.adjudication_state == 'awaiting_adjudication'


def test_revision_values_disagree_when_different(session):
    service, root, manifest, _ = session
    candidate = targets_of(service, root)['candidate']
    first = batch(session, (candidate, 'revise', None), submission='synthetic-a')
    first['opinions'][0]['proposed_value'] = {'value': 'Synthetic A'}
    service.submit(root, first)
    second = batch(session, (candidate, 'revise', None), submission='synthetic-b',
        reviewer='reviewer-b')
    second['opinions'][0]['proposed_value'] = {'value': 'Synthetic B'}
    service.submit(root, second)
    row = next(t for t in service.inspect(root).targets if t.target == candidate)
    assert row.agreement_state == 'disagreement'


def test_all_unable_is_pending_and_one_decisive_is_insufficient(session):
    service, root, manifest, target = session
    service.submit(root, batch(session, (target, 'unable_to_judge', None), submission='synthetic-a'))
    service.submit(root, batch(session, (target, 'unable_to_judge', None), submission='synthetic-b',
        reviewer='reviewer-b'))
    row = next(t for t in service.inspect(root).targets if t.target == target)
    assert row.agreement_state == 'pending' and row.unable_to_judge_count == 2
    service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-c',
        reviewer='reviewer-c'))
    row = next(t for t in service.inspect(root).targets if t.target == target)
    assert row.agreement_state == 'insufficient_opinions'
    assert row.unable_to_judge_count == 2 and len(row.latest_opinion_ids) == 3


# Row 7: only this reviewer's own head is a valid predecessor.
def test_previous_must_belong_to_same_reviewer_and_material(session):
    service, root, manifest, target = session
    first = service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    second = service.submit(root, batch(session, (target, 'accept', opinion_id(first)),
        submission='synthetic-b'))
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, batch(session, (target, 'reject', opinion_id(first)),
            submission='synthetic-c'))  # The old head is stale.
    assert exc.value.code == 'SESSION_STALE_WRITE'
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, batch(session, (target, 'reject', opinion_id(second)),
            submission='synthetic-d', reviewer='reviewer-b'))
    assert exc.value.code == 'SESSION_STALE_WRITE'  # Someone else's opinion.
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, batch(session, (target, 'reject', 'sessionopinion_' + 'f' * 24),
            submission='synthetic-e'))
    assert exc.value.code == 'SESSION_STALE_WRITE'  # Missing predecessor.


# Row 8: submission id idempotency and conflicts.
def test_same_submission_retry_is_idempotent_even_after_later_opinions(session):
    service, root, manifest, target = session
    first = service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-1'))
    service.submit(root, batch(session, (target, 'accept', opinion_id(first)), submission='synthetic-2'))
    before = snapshot(root / 'events')
    again = service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-1'))
    assert again.event_id == first.event_id
    assert snapshot(root / 'events') == before


@pytest.mark.parametrize('field', ['decision', 'reason', 'reviewer'])
def test_same_submission_id_with_different_content_conflicts(session, field):
    service, root, manifest, target = session
    service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-1'))
    changed = batch(session, (target, 'accept', None), submission='synthetic-1')
    if field == 'decision':
        changed['opinions'][0]['decision'] = 'reject'
    elif field == 'reason':
        changed['opinions'][0]['reason'] = 'Synthetic different reason'
    else:
        changed['reviewer']['reviewer_id'] = 'reviewer-b'
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, changed)
    assert exc.value.code == 'SESSION_SUBMISSION_CONFLICT'


# Row 9: undecodable events stay auditable but block writes.
def corrupt_event(session, damage):
    service, root, manifest, target = session
    healthy = service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    other = build_event(manifest, target, reviewer='reviewer-b', submission='synthetic-b')
    path = write_event(root, other)
    data = json.loads(path.read_text('utf-8'))
    if damage == 'content':
        data['event']['submission']['opinions'][0]['reason'] = 'Synthetic tamper'
        path.write_text(json.dumps(data), encoding='utf-8')
    elif damage == 'duplicate_key':
        body = path.read_text('utf-8').strip()
        path.write_text(body[:-1] + ', "event": {}, "event": {}}', encoding='utf-8')
    elif damage == 'unknown_version':
        data['event']['version'] = '0.2.0'
        data['sha256'] = content_hash(data['event'])
        path.write_text(json.dumps(data), encoding='utf-8')
    elif damage == 'unknown_wrapper_key':
        data['synthetic_extra'] = 1
        path.write_text(json.dumps(data), encoding='utf-8')
    elif damage == 'wrong_filename':
        path.rename(root / 'events' / ('sessionevent_' + 'a' * 24 + '.json'))
    else:
        # Self-consistent but not canonical: an offset timestamp instead of Z.
        data['event']['created_at'] = data['event']['created_at'].replace('Z', '+00:00')
        data['sha256'] = content_hash(data['event'])
        path.write_text(json.dumps(data), encoding='utf-8')
    return healthy


@pytest.mark.parametrize('damage', ['content', 'duplicate_key', 'unknown_version',
                                    'unknown_wrapper_key', 'wrong_filename', 'non_canonical'])
def test_corrupt_event_is_isolated_and_blocks_writes(session, damage):
    service, root, manifest, target = session
    corrupt_event(session, damage)
    view = service.inspect(root)
    assert not view.writable
    assert any(issue.code in {'SESSION_EVENT_INVALID', 'SESSION_SUBMISSION_CONFLICT'}
               for issue in view.issues)
    assert all(t.history_invalid and t.agreement_state == 'pending' for t in view.targets)
    assert len(view.opinions) == 1  # Healthy opinion stays auditable.
    before = snapshot(root / 'events')
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, batch(session, (target, 'reject', None), submission='synthetic-z'))
    assert exc.value.code == 'SESSION_HISTORY_INVALID'
    assert snapshot(root / 'events') == before


# Row 10: self-consistent events outside the binding are wholly isolated.
@pytest.mark.parametrize('kind', ['foreign_session', 'foreign_target'])
def test_self_consistent_foreign_event_isolated(session, kind):
    service, root, manifest, target = session
    if kind == 'foreign_session':
        event = build_event(manifest, target, submission='synthetic-x',
            session_id='reviewsession_' + '7' * 24)
    else:
        foreign = target.model_copy(update={'material_id': 'reviewitem_' + 'f' * 24})
        event = build_event(manifest, foreign, submission='synthetic-x')
    write_event(root, event)
    view = service.inspect(root)
    assert not view.writable
    assert [issue.code for issue in view.issues] == ['SESSION_EVENT_INVALID']
    assert view.opinions == []  # No half-valid batch.
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-y'))
    assert exc.value.code == 'SESSION_HISTORY_INVALID'


# Row 11: branches, dangling predecessors and deleted events block the session.
def test_second_root_for_same_reviewer_and_material_is_history_invalid(session):
    service, root, manifest, target = session
    other = targets_of(service, root)['anomaly']
    healthy = service.submit(root, batch(session, (other, 'accept', None), reviewer='reviewer-b',
        submission='synthetic-c'))
    first = build_event(manifest, target, submission='synthetic-a')
    second = build_event(manifest, target, submission='synthetic-b')
    write_event(root, first)
    write_event(root, second)
    view = service.inspect(root)
    assert not view.writable
    assert any(issue.code == 'SESSION_HISTORY_INVALID' for issue in view.issues)
    assert any(opinion.opinion_id == opinion_id(healthy) for opinion in view.opinions)
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-d'))
    assert exc.value.code == 'SESSION_HISTORY_INVALID'


def test_dangling_predecessor_is_history_invalid(session):
    service, root, manifest, target = session
    write_event(root, build_event(manifest, target, submission='synthetic-a',
        previous='sessionopinion_' + 'f' * 24))
    view = service.inspect(root)
    assert not view.writable and view.targets[0].agreement_state == 'pending'


def test_deleted_event_breaks_successor_chain(session):
    service, root, manifest, target = session
    first = build_event(manifest, target, submission='synthetic-a')
    second = build_event(manifest, target, submission='synthetic-b', previous=opinion_id(first))
    path = write_event(root, first)
    write_event(root, second)
    path.unlink()
    view = service.inspect(root)
    assert not view.writable
    assert any(issue.code == 'SESSION_HISTORY_INVALID' for issue in view.issues)


# Row 12: two events sharing a submission id invalidate the session.
def test_duplicate_submission_across_events_is_conflict(session):
    service, root, manifest, target = session
    write_event(root, build_event(manifest, target, submission='duplicate-1'))
    later = build_event(manifest, target, reviewer='reviewer-b', submission='duplicate-1',
        moment=datetime(2026, 1, 2, tzinfo=UTC), previous=None)
    write_event(root, later)
    view = service.inspect(root)
    assert any(issue.code == 'SESSION_SUBMISSION_CONFLICT' for issue in view.issues)
    assert not view.writable
    assert all(t.agreement_state == 'pending' and t.history_invalid for t in view.targets)


# Row 13: safe staging leftovers are ignored; unknown resources block writes.
def test_safe_pending_file_ignored_and_not_deleted(session):
    service, root, manifest, target = session
    orphan = root / 'events' / '.pending-session-event-orphan.tmp'
    orphan.write_bytes(b'synthetic staging leftovers')
    view = service.inspect(root)
    assert view.writable and not view.issues
    event = service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    assert orphan.exists() and event.event_id
    assert service.inspect(root).writable


@pytest.mark.parametrize('kind', ['file', 'directory'])
def test_unknown_event_resource_blocks_writes(session, kind):
    service, root, manifest, target = session
    path = root / 'events' / 'synthetic-unknown'
    path.write_bytes(b'unexpected') if kind == 'file' else path.mkdir()
    view = service.inspect(root)
    assert not view.writable
    assert any(issue.code == 'SESSION_EVENT_INVALID' for issue in view.issues)


def test_reparse_events_resource_skipped_without_link_privilege(session):
    service, root, manifest, target = session
    outside = root.parent / 'outside-events'
    outside.mkdir()
    try:
        os.symlink(outside, root / 'events' / 'linked', target_is_directory=True)
    except (OSError, NotImplementedError) as exc:
        pytest.skip('link creation unavailable in this environment: ' + type(exc).__name__)
    assert not service.inspect(root).writable


# Row 14: commit failures leave no visible half event and never overwrite targets.
def test_link_failure_rolls_back(session, monkeypatch):
    service, root, manifest, target = session
    before = snapshot(root / 'events')

    def broken_link(*args, **kwargs):
        raise OSError('synthetic link failure')

    monkeypatch.setattr(sessions_module.os, 'link', broken_link)
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    assert exc.value.code == 'SESSION_COMMIT_FAILED'
    assert snapshot(root / 'events') == before
    assert not list((root / 'events').glob('.pending-session-event-*'))


def test_fsync_failure_rolls_back(session, monkeypatch):
    service, root, manifest, target = session
    before = snapshot(root / 'events')

    def broken_fsync(fd):
        raise OSError('synthetic fsync failure')

    monkeypatch.setattr(sessions_module.os, 'fsync', broken_fsync)
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    assert exc.value.code == 'SESSION_COMMIT_FAILED'
    assert snapshot(root / 'events') == before


def test_publish_collision_never_replaces_existing_target(session):
    service, root, _, _ = session
    existing = root / 'events' / 'existing-target.json'
    existing.write_bytes(b'preexisting content')
    with pytest.raises(AnalysisError) as exc:
        ReviewSessionService._publish(existing, b'replacement payload')
    assert exc.value.code == 'SESSION_COMMIT_FAILED'
    assert existing.read_bytes() == b'preexisting content'
    assert not list((root / 'events').glob('.pending-session-event-*'))


# Row 15: a successful publication is not reported as failure.
def test_publish_success_survives_staging_cleanup_failure(session, monkeypatch):
    service, root, manifest, target = session
    real_unlink = Path.unlink

    def broken_unlink(self, *args, **kwargs):
        if self.name.startswith('.pending-session-event-'):
            raise OSError('synthetic cleanup failure')
        return real_unlink(self, *args, **kwargs)

    monkeypatch.setattr(Path, 'unlink', broken_unlink)
    event = service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    assert (root / 'events' / (event.event_id + '.json')).is_file()
    view = service.inspect(root)
    assert view.writable and len(view.opinions) == 1
    again = service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    assert again.event_id == event.event_id


# Row 16: concurrent writer lock yields SESSION_BUSY without damage.
LOCK_SCRIPT = '''
import msvcrt, sys, time
stream = open(sys.argv[1], 'a+b', buffering=0)
stream.seek(0)
if not stream.read(1):
    stream.write(b'0')
stream.seek(0)
msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
print('locked', flush=True)
time.sleep(60)
'''


@pytest.mark.skipif(os.name != 'nt', reason='msvcrt lock holder is Windows-only')
def test_busy_writer_lock_reports_session_busy(session):
    service, root, manifest, target = session
    lock = root / '.session-write.lock'
    process = subprocess.Popen([sys.executable, '-c', LOCK_SCRIPT, str(lock)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert process.stdout.readline().strip() == 'locked'
        with pytest.raises(AnalysisError) as exc:
            service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
        assert exc.value.code == 'SESSION_BUSY'
        assert not list((root / 'events').glob('sessionevent_*.json'))
    finally:
        process.kill()
        process.wait(timeout=30)
    service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    assert len(service.inspect(root).opinions) == 1


@pytest.mark.skipif(os.name != 'nt', reason='msvcrt lock holder is Windows-only')
def test_busy_create_lock_reports_session_busy(exported, tmp_path):
    preparation, packages, workspace = exported
    service = ReviewSessionService(packages, workspace)
    target = tmp_path / 'session'
    lock = target.parent / ('.session-create-' +
        stable_id('path', os.path.normcase(str(target.resolve())))[5:] + '.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen([sys.executable, '-c', LOCK_SCRIPT, str(lock)],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    try:
        assert process.stdout.readline().strip() == 'locked'
        with pytest.raises(AnalysisError) as exc:
            service.create(preparation, target)
        assert exc.value.code == 'SESSION_BUSY'
        assert not target.exists()
    finally:
        process.kill()
        process.wait(timeout=30)
    service.create(preparation, target)
    assert target.is_dir()


# Row 17: mutations during submit are detected before publishing.
@pytest.mark.parametrize('change', ['manifest', 'snapshot', 'package', 'events'])
def test_change_during_submit_detected(session, exported, monkeypatch, change):
    service, root, manifest, target = session
    packages = exported[1]
    original = ReviewSessionService._history

    def patched(self, context):
        result = original(self, context)
        if change == 'manifest':
            (root / 'session.json').write_bytes((root / 'session.json').read_bytes() + b' ')
        elif change == 'snapshot':
            path = root / 'preparation' / 'README.md'
            path.write_bytes(path.read_bytes() + b' ')
        elif change == 'package':
            package = next(packages.glob('*.medpkg'))
            package.write_bytes(package.read_bytes() + b'x')
        else:
            (root / 'events' / ('sessionevent_' + 'a' * 24 + '.json')).write_bytes(b'{}')
        return result

    monkeypatch.setattr(ReviewSessionService, '_history', patched)
    before = snapshot(root / 'events')
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    assert exc.value.code == 'SESSION_CHANGED'
    assert snapshot(root / 'events') == before or change == 'events'


# Row 18: limits and non-finite request values.
def test_event_byte_limit(session, monkeypatch):
    service, root, _, _ = session
    monkeypatch.setattr(sessions_module, 'MAX_EVENT_BYTES', 1)
    with pytest.raises(AnalysisError) as exc:
        service.inspect(root)
    assert exc.value.code == 'SESSION_LIMIT_EXCEEDED'


def test_history_byte_limit(session, monkeypatch):
    service, root, manifest, target = session
    service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    monkeypatch.setattr(sessions_module, 'MAX_HISTORY_BYTES', 1)
    with pytest.raises(AnalysisError) as exc:
        service.inspect(root)
    assert exc.value.code == 'SESSION_LIMIT_EXCEEDED'


def test_event_count_limit(session, monkeypatch):
    service, root, manifest, target = session
    service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    monkeypatch.setattr(sessions_module, 'MAX_EVENTS', 0)
    with pytest.raises(AnalysisError) as exc:
        service.inspect(root)
    assert exc.value.code == 'SESSION_LIMIT_EXCEEDED'


def test_non_finite_proposed_value_rejected(session):
    service, root, manifest, _ = session
    candidate = targets_of(service, root)['candidate']
    submission = batch(session, (candidate, 'revise', None), submission='synthetic-nan')
    submission['opinions'][0]['proposed_value'] = float('inf')
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, submission)
    assert exc.value.code == 'SESSION_REQUEST_INVALID'
    assert not list((root / 'events').glob('sessionevent_*.json'))


# Row 19: a copied session keeps its identity and can continue.
def test_moved_session_keeps_identity_and_continues(session, exported, tmp_path):
    service, root, manifest, target = session
    event = service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    old_session = snapshot(root)
    moved = tmp_path / 'moved'
    shutil.copytree(root, moved / 'session')
    shutil.copytree(exported[1], moved / 'packages')
    new_service = ReviewSessionService(moved / 'packages', moved / 'workspace-cache')
    view = new_service.inspect(moved / 'session')
    assert view.manifest.session_id == manifest.session_id
    assert [o.opinion_id for o in view.opinions] == [opinion_id(event)]
    assert view.opinions[0].opinion.reason == 'Self authored software opinion'
    again = new_service.submit(moved / 'session',
        batch(session, (target, 'accept', None), submission='synthetic-a'))
    assert again.event_id == event.event_id
    later = new_service.submit(moved / 'session',
        batch(session, (target, 'accept', None), reviewer='reviewer-c', submission='synthetic-c'))
    assert later.event_id != event.event_id
    assert snapshot(exported[1]) == snapshot(moved / 'packages')
    assert snapshot(root) == old_session


# Row 20: CLI end-to-end through a subprocess.
def cli(*arguments):
    return subprocess.run([sys.executable, '-m', 'medicine_agent.cli', 'analyze', *arguments],
        capture_output=True, encoding='utf-8', timeout=180)


def test_cli_create_inspect_submit_roundtrip(exported, tmp_path):
    preparation, packages, workspace = exported
    root = tmp_path / 'cli-session'
    before = snapshot(preparation), snapshot(packages)
    created = cli('review-session-create', '--preparation-dir', str(preparation),
        '--output-dir', str(root), '--packages', str(packages), '--workspace', str(workspace))
    assert created.returncode == 0, created.stdout + created.stderr
    manifest = json.loads(created.stdout)
    assert manifest['session_id'].startswith('reviewsession_')
    assert manifest['medical_review'] == 'unreviewed' and manifest['release_allowed'] is False

    summary = cli('review-session-inspect', '--session-dir', str(root),
        '--packages', str(packages), '--workspace', str(workspace))
    assert summary.returncode == 0
    payload = json.loads(summary.stdout)
    assert payload['opinion_count'] == 0 and payload['writable'] is True
    assert 'opinions' not in payload and 'state_counts' in payload

    service = ReviewSessionService(packages, workspace)
    target = next(t.target for t in service.inspect(root).targets if t.target.kind == 'candidate')
    submission = request((service, root, service.inspect(root).manifest, target))
    input_file = tmp_path / 'submission.json'
    input_file.write_text(json.dumps(submission), encoding='utf-8')
    submitted = cli('review-session-submit', '--session-dir', str(root),
        '--input-file', str(input_file), '--packages', str(packages),
        '--workspace', str(workspace))
    assert submitted.returncode == 0, submitted.stdout + submitted.stderr
    event = json.loads(submitted.stdout)
    assert event['opinion_count'] == 1 and event['reviewer_identity'] == 'self_declared'
    assert 'reason' not in submitted.stdout and 'proposed_value' not in submitted.stdout

    full = cli('review-session-inspect', '--session-dir', str(root), '--packages', str(packages),
        '--workspace', str(workspace), '--include-opinions')
    assert full.returncode == 0 and json.loads(full.stdout)['opinions']
    assert 'Self authored software opinion' in full.stdout
    assert (snapshot(preparation), snapshot(packages)) == before


@pytest.mark.parametrize('kind', ['duplicate_key', 'missing_version', 'unknown_version', 'preparation'])
def test_cli_submit_rejects_invalid_request_files(exported, tmp_path, kind):
    preparation, packages, workspace = exported
    root = tmp_path / 'cli-session'
    created = cli('review-session-create', '--preparation-dir', str(preparation),
        '--output-dir', str(root), '--packages', str(packages), '--workspace', str(workspace))
    assert created.returncode == 0
    service = ReviewSessionService(packages, workspace)
    target = next(t.target for t in service.inspect(root).targets if t.target.kind == 'candidate')
    submission = request((service, root, service.inspect(root).manifest, target))
    path = tmp_path / 'submission.json'
    if kind == 'duplicate_key':
        path.write_text(json.dumps(submission)[:-1] + ', "version": "0.1.0"}', encoding='utf-8')
    elif kind == 'missing_version':
        submission.pop('version')
        path.write_text(json.dumps(submission), encoding='utf-8')
    elif kind == 'unknown_version':
        submission['version'] = '0.2.0'
        path.write_text(json.dumps(submission), encoding='utf-8')
    else:
        path.write_text((preparation / 'preparation.json').read_text('utf-8'), encoding='utf-8')
    result = cli('review-session-submit', '--session-dir', str(root), '--input-file', str(path),
        '--packages', str(packages), '--workspace', str(workspace))
    assert result.returncode == 1
    assert json.loads(result.stdout)['error']['code'] == 'SESSION_REQUEST_INVALID'
    assert not list((root / 'events').glob('sessionevent_*.json'))


def test_cli_inspect_and_submit_on_corrupt_session(session, exported):
    service, root, manifest, target = session
    event = service.submit(root, batch(session, (target, 'accept', None), submission='synthetic-a'))
    path = root / 'events' / (event.event_id + '.json')
    data = json.loads(path.read_text('utf-8'))
    data['event']['submission']['opinions'][0]['reason'] = 'Synthetic tamper'
    path.write_text(json.dumps(data), encoding='utf-8')
    packages, workspace = exported[1], exported[2]
    inspected = cli('review-session-inspect', '--session-dir', str(root),
        '--packages', str(packages), '--workspace', str(workspace))
    assert inspected.returncode == 0
    payload = json.loads(inspected.stdout)
    assert payload['writable'] is False and payload['issues'][0]['code'] == 'SESSION_EVENT_INVALID'
    assert 'Synthetic tamper' not in inspected.stdout
    input_file = root.parent / 'submission.json'
    input_file.write_text(json.dumps(request((service, root, manifest, target))), encoding='utf-8')
    submitted = cli('review-session-submit', '--session-dir', str(root),
        '--input-file', str(input_file), '--packages', str(packages),
        '--workspace', str(workspace))
    assert submitted.returncode == 1
    assert json.loads(submitted.stdout)['error']['code'] == 'SESSION_HISTORY_INVALID'


# D05: limits must also reject before publication, after healthy history is read.
@pytest.mark.parametrize('limit_kind', ['event_bytes', 'history_bytes', 'event_count'])
def test_submit_capacity_before_publication(session, exported, monkeypatch, limit_kind):
    service, root, _, target = session
    if limit_kind != 'event_bytes':
        service.submit(root, request(session))
    before = snapshot(root / 'events'), snapshot(exported[1]), snapshot(root / 'preparation')
    incoming = request(session, reviewer='capacity-reviewer', submission='capacity-new', decision='revise')
    if limit_kind == 'event_bytes':
        monkeypatch.setattr(sessions_module, 'MAX_EVENT_BYTES', (root / 'session.json').stat().st_size + 1024)
        incoming['opinions'][0]['proposed_value'] = 'Synthetic capacity value ' * 4096
    elif limit_kind == 'history_bytes':
        existing = sum(p.stat().st_size for p in (root / 'events').iterdir())
        monkeypatch.setattr(sessions_module, 'MAX_HISTORY_BYTES', existing + 1)
    else:
        monkeypatch.setattr(sessions_module, 'MAX_EVENTS', 1)
    assert service.inspect(root).writable  # The read path must still succeed.
    monkeypatch.setattr(ReviewSessionService, '_publish',
        lambda *args: pytest.fail('An over-limit batch reached publication'))
    with pytest.raises(AnalysisError) as exc:
        service.submit(root, incoming)
    assert exc.value.code == 'SESSION_LIMIT_EXCEEDED'
    assert (snapshot(root / 'events'), snapshot(exported[1]), snapshot(root / 'preparation')) == before
