"""Package-external review sessions with atomic, append-only batch events."""
from collections import Counter, defaultdict
from datetime import UTC, datetime
from functools import wraps
import json
import os
from pathlib import Path
import re
import shutil
import stat
import tempfile

from pydantic import ValidationError

from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.review_snapshot import (
    _json_object, _read_file, _read_snapshot, _safe_path, _signature,
    load_preparation_snapshot,
)
from medicine_agent.analysis.store import atomic_json, process_lock
from medicine_agent.domain.ids import canonical_json, content_hash, file_sha256, stable_id
from medicine_agent.domain.review_session import (
    ReviewSessionManifest, ReviewSessionView, SessionEvent, SessionIssue,
    SessionOpinionRecord, SessionSnapshotBinding, SessionSubmission, SessionTarget,
    TargetReviewSummary,
)


MAX_EVENT_BYTES = 64 * 1024 * 1024
MAX_HISTORY_BYTES = 128 * 1024 * 1024
MAX_EVENTS = 10000


def _fail(code):
    raise AnalysisError(code, 'Review session operation failed: ' + code) from None


def _guard(method):
    @wraps(method)
    def call(*args, **kwargs):
        try:
            return method(*args, **kwargs)
        except AnalysisError as exc:
            if exc.code.startswith('SESSION_'):
                _fail(exc.code)
            if exc.code == 'SNAPSHOT_LIMIT_EXCEEDED':
                _fail('SESSION_LIMIT_EXCEEDED')
            _fail('SESSION_BUSY' if exc.code == 'TASK_BUSY' else 'SESSION_SNAPSHOT_INVALID')
        except (OSError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
            _fail('SESSION_IO_ERROR')
    return call


def _key(target):
    return target.kind, target.material_id


def _session_path(value):
    try:
        return _safe_path(value)
    except (AnalysisError, OSError, ValueError):
        _fail('SESSION_PATH_INVALID')


def _overlap(paths):
    return any(a.is_relative_to(b) or b.is_relative_to(a)
        for i, a in enumerate(paths) for b in paths[i + 1:])


def _unwrap(data, field, model, code):
    try:
        wrapper = _json_object(data)
        if set(wrapper) != {field, 'sha256'}:
            _fail(code)
        payload = wrapper[field]
        if not isinstance(payload, dict) or payload.get('version') != '0.1.0':
            _fail(code)
        if model is SessionEvent and payload.get('submission', {}).get('version') != '0.1.0':
            _fail(code)
        if content_hash(payload) != wrapper['sha256']:
            _fail(code)
        value = model.model_validate(payload)
        if payload != value.model_dump(mode='json'):
            _fail(code)
        identity_field, prefix = ('event_id', 'sessionevent') if model is SessionEvent else ('session_id', 'reviewsession')
        if getattr(value, identity_field) != stable_id(prefix,
                value.model_dump(mode='json', exclude={identity_field})):
            _fail(code)
        return value
    except (AnalysisError, ValueError, TypeError, KeyError, AttributeError, RecursionError):
        _fail(code)


def _binding(validated, files):
    archives = {r.address.archive: r.address.archive_sha256
        for r in validated.report.coverage.records if r.address is not None}
    return SessionSnapshotBinding(snapshot_id=validated.snapshot_id,
        preparation_id=validated.report.preparation_id, manifest_sha256=validated.manifest_sha256,
        snapshot_files={name: file_sha256(data) for name, data in files.items()}, source_archives=archives)


def _targets(validated):
    sid = validated.snapshot_id
    result = {}
    for kind, items, id_field in (
            ('source_annotation', validated.report.sources, 'annotation_id'),
            ('candidate', validated.report.candidates, 'item_id'),
            ('anomaly', validated.report.anomalies, 'anomaly_id')):
        for item in items:
            target = SessionTarget(snapshot_id=sid, kind=kind, material_id=getattr(item, id_field),
                review_target=item.target if kind == 'candidate' else None)
            if _key(target) in result:
                _fail('SESSION_SNAPSHOT_INVALID')
            result[_key(target)] = target
    return result


def _pending(name):
    return name.startswith('.pending-session-event-') and name.endswith('.tmp')


def _event_state(directory):
    result = {}
    for path in directory.iterdir():
        info = path.lstat()
        # Orphaned safe staging files are not committed history.
        if _pending(path.name) and stat.S_ISREG(info.st_mode) and not (
                getattr(info, 'st_file_attributes', 0) & 0x400):
            continue
        result[path.name] = (*_signature(info), info.st_mode,
            getattr(info, 'st_file_attributes', 0))
    return result


class ReviewSessionService:
    """Management API only. Neither source packages nor worksheets are written."""

    @_guard
    def __init__(self, packages, workspace):
        self.packages, self.workspace = map(_session_path, (packages, workspace))
        if _overlap((self.packages, self.workspace)):
            _fail('SESSION_PATH_INVALID')

    def _root(self, value):
        root = _session_path(value)
        if _overlap((root, self.packages, self.workspace)):
            _fail('SESSION_PATH_INVALID')
        return root

    @_guard
    def create(self, preparation_dir, output_dir):
        preparation, target = _session_path(preparation_dir), self._root(output_dir)
        if _overlap((preparation, target, self.packages, self.workspace)):
            _fail('SESSION_PATH_INVALID')
        if target.exists():
            _fail('SESSION_EXISTS')
        original = load_preparation_snapshot(preparation, packages=self.packages, workspace=self.workspace)
        files = _read_snapshot(preparation)
        target.parent.mkdir(parents=True, exist_ok=True)
        lock = target.parent / ('.session-create-' + stable_id('path', os.path.normcase(str(target)))[5:] + '.lock')
        _session_path(lock)
        with process_lock(lock):
            if target.exists():
                _fail('SESSION_EXISTS')
            stage = Path(tempfile.mkdtemp(prefix='.pending-review-session-', dir=target.parent))
            try:
                (stage / 'preparation').mkdir()
                (stage / 'events').mkdir()
                for name, data in files.items():
                    (stage / 'preparation' / name).write_bytes(data)
                copied = load_preparation_snapshot(stage / 'preparation',
                    packages=self.packages, workspace=self.workspace)
                if copied.snapshot_id != original.snapshot_id:
                    _fail('SESSION_CHANGED')
                manifest = ReviewSessionManifest(session_id='reviewsession_' + '0' * 24,
                    created_at=datetime.now(UTC), binding=_binding(copied, files))
                manifest.session_id = stable_id('reviewsession',
                    manifest.model_dump(mode='json', exclude={'session_id'}))
                payload = manifest.model_dump(mode='json')
                atomic_json(stage / 'session.json', {'manifest': payload, 'sha256': content_hash(payload)})
                if target.exists():
                    _fail('SESSION_EXISTS')
                try:
                    stage.rename(target)
                except FileExistsError:
                    _fail('SESSION_EXISTS')
                return manifest
            finally:
                # Only clean the private directory created by this operation.
                if stage.exists() and not stage.is_symlink() and stage.resolve().parent == target.parent:
                    shutil.rmtree(stage)

    def _context(self, session_dir):
        root = self._root(session_dir)
        if not root.is_dir():
            _fail('SESSION_PATH_INVALID')
        entries = {p.name for p in root.iterdir()}
        if not {'session.json', 'preparation', 'events'} <= entries or entries - {
                'session.json', 'preparation', 'events', '.session-write.lock'}:
            _fail('SESSION_MANIFEST_INVALID')
        for name in entries:
            path = _session_path(root / name)
            mode = path.lstat().st_mode
            if not (stat.S_ISDIR(mode) if name in {'preparation', 'events'} else stat.S_ISREG(mode)):
                _fail('SESSION_PATH_INVALID')
        raw = _read_file(root / 'session.json', limit=MAX_EVENT_BYTES)
        manifest = _unwrap(raw, 'manifest', ReviewSessionManifest, 'SESSION_MANIFEST_INVALID')
        validated = load_preparation_snapshot(root / 'preparation',
            packages=self.packages, workspace=self.workspace)
        files = _read_snapshot(root / 'preparation')
        if manifest.binding != _binding(validated, files):
            _fail('SESSION_SNAPSHOT_INVALID')
        return dict(root=root, manifest=manifest, raw_manifest=raw, snapshot_files=files,
            targets=_targets(validated), event_state=_event_state(root / 'events'))

    def _unchanged(self, context):
        try:
            root, manifest = context['root'], context['manifest']
            if (_read_file(root / 'session.json', limit=MAX_EVENT_BYTES) != context['raw_manifest'] or
                    _read_snapshot(root / 'preparation') != context['snapshot_files'] or
                    _event_state(root / 'events') != context['event_state']):
                _fail('SESSION_CHANGED')
            for name, expected in manifest.binding.source_archives.items():
                if file_sha256(_read_file(self.packages / name)) != expected:
                    _fail('SESSION_CHANGED')
        except (AnalysisError, OSError, ValueError, TypeError):
            _fail('SESSION_CHANGED')

    def _history(self, context):
        root, manifest, targets = context['root'], context['manifest'], context['targets']
        events, issues, records = [], [], []
        entries = context['event_state']
        if len(entries) > MAX_EVENTS:
            _fail('SESSION_LIMIT_EXCEEDED')
        total = 0
        for name in sorted(entries):
            try:
                if re.fullmatch(r'sessionevent_[0-9a-f]{24}\.json', name) is None:
                    _fail('SESSION_EVENT_INVALID')
                path = root / 'events' / name
                total += path.lstat().st_size
                if total > MAX_HISTORY_BYTES:
                    _fail('SESSION_LIMIT_EXCEEDED')
                event = _unwrap(_read_file(path, limit=MAX_EVENT_BYTES), 'event',
                    SessionEvent, 'SESSION_EVENT_INVALID')
                if name != event.event_id + '.json' or event.submission.session_id != manifest.session_id:
                    _fail('SESSION_EVENT_INVALID')
                if any(targets.get(_key(o.target)) != o.target for o in event.submission.opinions):
                    _fail('SESSION_EVENT_INVALID')
                events.append(event)
                for index, opinion in enumerate(event.submission.opinions):
                    records.append(SessionOpinionRecord(opinion_id=stable_id('sessionopinion',
                        {'event_id': event.event_id, 'opinion_index': index}), event_id=event.event_id,
                        opinion_index=index, created_at=event.created_at,
                        reviewer=event.submission.reviewer, opinion=opinion))
            except (AnalysisError, OSError, ValueError, TypeError, KeyError, AttributeError) as exc:
                if isinstance(exc, AnalysisError) and exc.code in {
                        'SESSION_LIMIT_EXCEEDED', 'SNAPSHOT_LIMIT_EXCEEDED'}:
                    _fail('SESSION_LIMIT_EXCEEDED')
                issues.append(SessionIssue(code='SESSION_EVENT_INVALID', event_file=name))
        submissions = Counter(e.submission.submission_id for e in events)
        if any(n > 1 for n in submissions.values()):
            issues.append(SessionIssue(code='SESSION_SUBMISSION_CONFLICT'))
        groups = defaultdict(list)
        for record in records:
            groups[(record.reviewer.reviewer_id, _key(record.opinion.target))].append(record)
        heads, invalid_targets = {}, set()
        for key, values in groups.items():
            by_id = {v.opinion_id: v for v in values}
            previous = [v.opinion.expected_previous_id for v in values]
            roots = [v for v in values if v.opinion.expected_previous_id is None]
            tips = [v for v in values if v.opinion_id not in previous]
            bad = (len(by_id) != len(values) or len(roots) != 1 or len(tips) != 1 or
                any(n > 1 for n in Counter(previous).values()) or
                any(p is not None and p not in by_id for p in previous))
            if not bad:
                seen, current = set(), tips[0].opinion_id
                while current is not None and current not in seen:
                    seen.add(current)
                    current = by_id[current].opinion.expected_previous_id
                bad = current is not None or len(seen) != len(values)
            if bad:
                invalid_targets.add(key[1])
                issues.append(SessionIssue(code='SESSION_HISTORY_INVALID'))
            else:
                heads[key] = tips[0]
        summaries = []
        unknown_history = any(issue.code != 'SESSION_HISTORY_INVALID' for issue in issues)
        for key, target in sorted(targets.items()):
            latest = [r for (_, material), r in heads.items() if material == key]
            decisive = [r for r in latest if r.opinion.decision != 'unable_to_judge']
            choices = {canonical_json([r.opinion.decision, r.opinion.proposed_value]) for r in decisive}
            # An undecodable event may contain an unknown successor for any
            # material. Preserve healthy opinions but never imply a final head.
            invalid = unknown_history or key in invalid_targets
            state = ('pending' if invalid or not decisive else 'insufficient_opinions'
                if len(decisive) == 1 else 'agreement' if len(choices) == 1 else 'disagreement')
            summaries.append(TargetReviewSummary(target=target, agreement_state=state,
                adjudication_state='awaiting_adjudication' if state == 'disagreement' else 'not_required',
                latest_opinion_ids=sorted(r.opinion_id for r in latest),
                unable_to_judge_count=sum(r.opinion.decision == 'unable_to_judge' for r in latest),
                history_invalid=invalid))
        view = ReviewSessionView(manifest=manifest, opinions=records, targets=summaries,
            issues=issues, writable=not issues)
        return view, events, heads

    @_guard
    def inspect(self, session_dir):
        context = self._context(session_dir)
        view, _, _ = self._history(context)
        self._unchanged(context)
        return view

    @_guard
    def submit(self, session_dir, request):
        try:
            raw = request.model_dump(mode='json') if isinstance(request, SessionSubmission) else request
            request = SessionSubmission.model_validate(raw)
            # Reject non-finite correction values before any event is created.
            json.dumps(request.model_dump(mode='json'), allow_nan=False)
        except (ValidationError, ValueError, TypeError):
            _fail('SESSION_REQUEST_INVALID')
        root = self._root(session_dir)
        if not root.is_dir():
            _fail('SESSION_PATH_INVALID')
        _session_path(root / '.session-write.lock')
        with process_lock(root / '.session-write.lock'):
            context = self._context(root)
            view, events, heads = self._history(context)
            if not view.writable:
                _fail('SESSION_HISTORY_INVALID')
            if request.session_id != context['manifest'].session_id:
                _fail('SESSION_REQUEST_INVALID')
            for previous in events:
                if previous.submission.submission_id == request.submission_id:
                    if previous.submission == request:
                        self._unchanged(context)
                        return previous
                    _fail('SESSION_SUBMISSION_CONFLICT')
            for opinion in request.opinions:
                if context['targets'].get(_key(opinion.target)) != opinion.target:
                    _fail('SESSION_TARGET_INVALID')
                tip = heads.get((request.reviewer.reviewer_id, _key(opinion.target)))
                if opinion.expected_previous_id != (tip.opinion_id if tip else None):
                    _fail('SESSION_STALE_WRITE')
            event = SessionEvent(event_id='sessionevent_' + '0' * 24,
                created_at=datetime.now(UTC), submission=request)
            event.event_id = stable_id('sessionevent', event.model_dump(mode='json', exclude={'event_id'}))
            payload = event.model_dump(mode='json')
            data = canonical_json({'event': payload, 'sha256': content_hash(payload)}).encode('utf-8')
            if len(data) > MAX_EVENT_BYTES or len(context['event_state']) >= MAX_EVENTS or (
                    sum(info[2] for info in context['event_state'].values()) + len(data) > MAX_HISTORY_BYTES):
                _fail('SESSION_LIMIT_EXCEEDED')
            self._unchanged(context)
            self._publish(root / 'events' / (event.event_id + '.json'), data)
            return event

    @staticmethod
    def _publish(target, data):
        fd, name = tempfile.mkstemp(prefix='.pending-session-event-', suffix='.tmp', dir=target.parent)
        pending = Path(name)
        try:
            with os.fdopen(fd, 'wb') as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            # Atomic publication without replacement; never use os.replace here.
            os.link(pending, target)
        except OSError:
            _fail('SESSION_COMMIT_FAILED')
        finally:
            # Publication may already have succeeded. An orphaned staging file
            # must not turn that success into an ambiguous failed response.
            try:
                pending.unlink(missing_ok=True)
            except OSError:
                pass
