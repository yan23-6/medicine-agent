"""Atomic candidate revisions from explicitly selected, current review proposals."""
import json
import shutil
from datetime import datetime, UTC

from pydantic import ValidationError

from medicine_agent.analysis.associations import node_index
from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.reviews import read_reviews, target_value
from medicine_agent.analysis.store import atomic_json, digest, process_lock
from medicine_agent.domain.corrections import CorrectionRequest, CorrectionEvent, CorrectionBundle
from medicine_agent.domain.ids import stable_id, file_sha256
from medicine_agent.domain.reviews import ReviewRecord
from medicine_agent.packages.corrections import apply_reviews, correction_identity, read_corrections, revised_metadata
from medicine_agent.packages.io import validate_package_path, read_jsonl, write_jsonl
from medicine_agent.packages.tcm import read_graph


def revise_candidate(catalog, request):
    try:
        request = CorrectionRequest.model_validate(request)
    except ValidationError as exc:
        raise AnalysisError('CORRECTION_REQUEST_INVALID', 'Supply a parent path and unique review IDs') from exc
    # Serialize reviews, selection and revisions in a fixed lock order.
    with process_lock(catalog.root / '.review-write.lock'), process_lock(catalog.root / '.selection.lock'):
        parent = catalog._path(request.parent_path)
        if not validate_package_path(parent).valid:
            raise AnalysisError('PARENT_REVISION_INVALID', 'Parent package is missing or invalid')
        manifest = json.loads((parent / 'manifest.json').read_text('utf-8'))
        revision_path = parent / 'revision.json'
        graph = read_graph(parent)
        if not graph or not revision_path.exists() or 'revision.json' not in manifest['files']:
            raise AnalysisError('CORRECTION_PARENT_UNSUPPORTED', 'A versioned TCM package is required')
        previous = json.loads(revision_path.read_text('utf-8'))
        with process_lock(catalog.root / ('.family-' + digest(previous['family']) + '.lock')):
            history = read_reviews(catalog)
            if history['errors']:
                raise AnalysisError('REVIEW_HISTORY_INVALID', 'Review storage contains invalid records')
            records = {r['review_id']: r for r in history['records']}
            chosen = []
            index = node_index(catalog)
            for rid in sorted(request.review_ids):
                if rid not in records:
                    raise AnalysisError('CORRECTION_REVIEW_UNAVAILABLE', 'Selected review record is unavailable')
                record = ReviewRecord.model_validate(records[rid])
                state = history['states'][digest(record.request.target.model_dump(mode='json'))]
                if state['user_review_state'] == 'history_invalid':
                    raise AnalysisError('REVIEW_HISTORY_INVALID', 'Selected review history is conflicting')
                if state['latest_review_id'] != rid:
                    raise AnalysisError('CORRECTION_REVIEW_STALE', 'Use the latest review for each target')
                target_value(record.request.target, index)
                chosen.append(record)
            try:
                updated, mapping = apply_reviews(graph, manifest['package_id'], chosen)
            except (ValueError, TypeError, KeyError) as exc:
                raise AnalysisError('CORRECTION_PROPOSAL_INVALID', str(exc)) from exc
            package_id = correction_identity(manifest['package_id'], chosen)
            target = catalog._path('revisions/' + package_id)
            if target.exists():
                if not validate_package_path(target).valid:
                    raise AnalysisError('CORRECTION_OUTPUT_INVALID', 'Existing correction output is invalid')
                audit = read_corrections(target)
                if audit is None or audit.history[-1].package_id != package_id:
                    raise AnalysisError('CORRECTION_OUTPUT_INVALID', 'Existing output belongs to another operation')
                return _result(catalog, target, audit)
            selected = [i for i in catalog.selected() if i['family'] == previous['family']]
            if not selected or selected[0]['package_id'] != manifest['package_id']:
                raise AnalysisError('PARENT_REVISION_CONFLICT', 'Select the parent revision before correcting it')
            staging = catalog._path('.pending-correction-' + package_id)
            if staging != catalog.root / ('.pending-correction-' + package_id):
                raise AnalysisError('PACKAGE_PATH_INVALID', 'Staging path must not be redirected')
            if staging.exists():
                # An earlier failed/crashed attempt is never visible in the catalog.
                shutil.rmtree(staging)
            staging.mkdir()
            try:
                # Only manifest resources are inherited, never local PDF snapshots or symlinks.
                for name in manifest['files']:
                    source = parent / name
                    destination = staging / name
                    if not destination.resolve().is_relative_to(staging) or source.is_symlink():
                        raise AnalysisError('PACKAGE_PATH_INVALID', 'Unsafe inherited package resource')
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copyfile(source, destination)
                projected = read_jsonl(staging / 'knowledge.jsonl')
                by_id = {n.node_id: n for n in updated.nodes}
                for item in projected:
                    old = item['knowledge_id']
                    if old in mapping:
                        node = by_id[mapping[old]]
                        item.update(knowledge_id=node.node_id, statement=node.statement, label=node.title)
                write_jsonl(staging / 'knowledge.jsonl', projected)
                relations = read_jsonl(staging / 'relations.jsonl')
                for item in relations:
                    before_endpoints = (item['source_knowledge_id'], item['target_knowledge_id'])
                    for endpoint in ('source_knowledge_id', 'target_knowledge_id'):
                        item[endpoint] = mapping.get(item[endpoint], item[endpoint])
                    if before_endpoints != (item['source_knowledge_id'], item['target_knowledge_id']):
                        item['relation_id'] = stable_id('rel', {k: v for k, v in item.items() if k != 'relation_id'})
                write_jsonl(staging / 'relations.jsonl', relations)
                atomic_json(staging / 'tcm.json', updated.model_dump(mode='json'))
                new_revision = revised_metadata(previous, package_id, updated)
                atomic_json(staging / 'revision.json', new_revision)
                changed = {'tcm.json', 'knowledge.jsonl', 'relations.jsonl', 'revision.json', 'corrections.json'}
                ancestor_ids = set()
                for chosen_record in chosen:
                    current = chosen_record.review_id
                    while current is not None:
                        ancestor_ids.add(current)
                        current = records[current]['request']['expected_previous_id']
                event = CorrectionEvent(parent_package_id=manifest['package_id'], package_id=package_id,
                    parent_revision=previous, parent_graph=graph, reviews=chosen, node_mapping=mapping,
                    review_history=[ReviewRecord.model_validate(records[rid]) for rid in sorted(ancestor_ids)],
                    preserved_files={k: v for k, v in manifest['files'].items() if k not in changed})
                prior = read_corrections(parent)
                audit = CorrectionBundle(history=(prior.history if prior else []) + [event])
                atomic_json(staging / 'corrections.json', audit.model_dump(mode='json'))
                files = set(manifest['files']) | {'corrections.json'}
                output = {**manifest, 'package_id': package_id, 'created_at': datetime.now(UTC).isoformat(),
                          'files': {name: file_sha256((staging / name).read_bytes()) for name in files}}
                atomic_json(staging / 'manifest.json', output)
                atomic_json(staging / 'checksums.json', output['files'])
                if not validate_package_path(staging).valid:
                    raise AnalysisError('CORRECTION_VALIDATION_FAILED', 'Corrected package failed validation')
                # Recheck the parent before the only visible commit.
                if not validate_package_path(parent).valid or json.loads((parent/'manifest.json').read_text('utf-8')) != manifest:
                    raise AnalysisError('PARENT_REVISION_INVALID', 'Parent changed during correction')
                target.parent.mkdir(parents=True, exist_ok=True)
                staging.rename(target)
            finally:
                if staging.exists():
                    shutil.rmtree(staging)
            return _result(catalog, target, audit)


def _result(catalog, path, audit):
    return {'package_path': path.relative_to(catalog.root).as_posix(),
            'package_id': audit.history[-1].package_id, 'status': 'research_candidate',
            'activation': 'explicit_selection_required', 'medical_review': 'unreviewed',
            'correction': audit.model_dump(mode='json')}
