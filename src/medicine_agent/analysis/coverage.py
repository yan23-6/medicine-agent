"""Read-only package coverage with conservative, deterministic incremental plans."""
import json
from pathlib import Path

from medicine_agent.analysis.library import PackageLibrary
from medicine_agent.analysis.models import AnalysisError, PackageRevision
from medicine_agent.domain.coverage import (CoverageAddress, CoverageDecision, CoverageInventory,
    CoverageIssue, CoveragePlan, CoveragePolicy, CoverageRecord, CoverageRequest)
from medicine_agent.domain.ids import file_sha256, stable_id
from medicine_agent.packages.io import read_jsonl
from medicine_agent.packages.owned import read_owned_cache

STAGES = ('extraction', 'semantic_candidate')


def _key(model):
    return json.dumps(model.model_dump(mode='json'), sort_keys=True, ensure_ascii=False)


def _unique(items):
    return [value for _, value in sorted({_key(item): item for item in items}.items())]


def _units(value, count):
    if (not isinstance(value, list) or not value or len(value) > 100000 or
        any(type(u) is not int or not 1 <= u <= count for u in value) or
        len(set(value)) != len(value)):
        raise ValueError('Invalid coverage units')
    return sorted(value)


class CoverageService:
    """Management API, not an Agent tool. Only private unpack caches may be written."""

    def __init__(self, packages: Path, workspace: Path):
        if Path(packages).resolve().is_relative_to(Path(workspace).resolve()):
            raise AnalysisError('WORKSPACE_LOCATION_INVALID', 'Keep coverage cache and package directory non-nested')
        self.library = PackageLibrary(packages, workspace)

    def inventory(self) -> CoverageInventory:
        records, issues = [], []
        try:
            files = sorted(p for p in self.library.root.iterdir() if p.suffix.lower() == '.medpkg')
        except OSError:
            return CoverageInventory(records=[], issues=[CoverageIssue(
                code='PACKAGE_ROOT_UNAVAILABLE', reason='Package directory missing or unreadable; not proof of no coverage')])
        for file in files:
            try:
                if not file.resolve().is_relative_to(self.library.root):
                    raise ValueError('Redirected archive')
                sha = file_sha256(file.read_bytes())
                root, bundle = self.library.load(file)
                pending = []
                for component in sorted(bundle.components, key=lambda c: c.path):
                    pending.extend(self._component(root / component.path, CoverageAddress(
                        archive=file.name, archive_sha256=sha, bundle_id=bundle.bundle_id,
                        package_id=component.package_id, manifest_sha256=component.manifest_sha256, component=component.path,
                        active=component.active, resources=['sources.jsonl', 'evidence.jsonl'])))
                if file_sha256(file.read_bytes()) != sha:
                    raise ValueError('Archive changed during scan')
                records.extend(pending)
            except (AnalysisError, OSError, ValueError, KeyError, TypeError, AttributeError):
                # Never publish partial coverage from an invalid file, or echo raw metadata.
                issues.append(CoverageIssue(code='PACKAGE_QUARANTINED', archive=file.name,
                    reason='Integrity, identity, source, resources or coverage range invalid; other packages continue'))
        return CoverageInventory(records=_unique(records), issues=_unique(issues))

    def _component(self, path, address):
        sources = read_jsonl(path / 'sources.jsonl')
        if not sources:
            raise ValueError('No source')
        for source in sources:
            sha = source['sha256']
            if (len(sha) != 64 or any(c not in '0123456789abcdef' for c in sha) or
                source['source_id'] != stable_id('src', {'sha256': sha})):
                raise ValueError('Source fingerprint identity mismatch')
        # Old valid sources have no recoverable stage boundary. Do not infer from titles.
        if not (path / 'revision.json').exists():
            return [CoverageRecord(source_sha256=s['sha256'], source_id=s['source_id'],
                stage=stage, state='unknown', reason='REVISION_MISSING', address=address,
                integrity_basis=['archive_and_components_validated']) for s in sources for stage in STAGES]
        manifest = json.loads((path / 'manifest.json').read_text('utf-8'))
        if 'revision.json' not in manifest['files'] or len(sources) != 1:
            raise ValueError('Unprotected or ambiguous revision')
        revision = PackageRevision.model_validate_json((path / 'revision.json').read_text('utf-8'))
        source = sources[0]
        if revision.source_sha256 != source['sha256']:
            raise ValueError('Revision points to different source')
        address = address.model_copy(update={'family': revision.family, 'parent': revision.parent,
            'resources': address.resources + ['revision.json']})
        kind = {'application/pdf': 'physical_page', 'text/plain': 'text_line',
            'image/png': 'image', 'image/jpeg': 'image',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'structured_unit'
            }.get(source['media_type'], 'unknown')
        common = dict(source_sha256=source['sha256'], source_id=source['source_id'],
            unit_kind=kind, address=address, integrity_basis=['archive_and_components_validated',
                'source_fingerprint_identity_matched', 'revision_hash_validated'])
        scope = revision.processing_scope
        if not isinstance(scope, dict) or scope.get('document_unit_count') is None:
            return [CoverageRecord(**common, stage=stage, state='unknown',
                reason='DOCUMENT_SCOPE_MISSING') for stage in STAGES]
        count = scope['document_unit_count']
        if type(count) is not int or not 1 <= count <= 100000:
            raise ValueError('Invalid document size')
        selected = _units(revision.units, count)
        selected_set = set(selected)
        if _units(scope.get('selected_units'), count) != selected:
            raise ValueError('Revision scope differs')
        common.update(document_unit_count=count, units=selected)
        evidence = read_jsonl(path / 'evidence.jsonl')
        observed = set()
        methods = {}
        missing_units, unlocated = set(), False
        for record in evidence:
            loc = record['location']
            if record['source_id'] != source['source_id']:
                raise ValueError('Evidence points to different source')
            if loc.get('source_sha256') is not None and loc['source_sha256'] != source['sha256']:
                raise ValueError('Evidence fingerprint differs')
            if loc.get('unit') is None:
                unlocated = True
                continue
            unit = loc['unit']
            if type(unit) is not int or unit not in selected_set:
                raise ValueError('Evidence unit outside scope')
            if kind == 'physical_page' and loc.get('page') is not None and (type(loc['page']) is not int or loc['page'] != unit):
                raise ValueError('Physical page differs from unit')
            if kind != 'physical_page' and loc.get('page') is not None:
                raise ValueError('Non-PDF cannot claim physical pages')
            if loc.get('source_sha256') is None or (kind == 'physical_page' and loc.get('page') is None):
                missing_units.add(unit)
                continue
            observed.add(unit)
            if isinstance(loc.get('method'), str):
                methods.setdefault(unit, set()).add(loc['method'])
        cache = read_owned_cache(path)
        if cache and cache.document_unit_count != count:
            raise ValueError('Cache document size differs')
        runtime = revision.runtime or {}
        cached_units = {u.ordinal: u for u in cache.units} if cache else {}
        policy = CoveragePolicy(analysis_policy=runtime.get('analysis_policy'),
            context_policy=runtime.get('context_policy'), semantic_version=runtime.get('semantics'))
        adapters = runtime.get('adapters', {})
        if not isinstance(adapters, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in adapters.items()):
            adapters = {}
        result = []
        for unit in selected:
            base = dict(common, units=[unit])
            state = 'verified' if unit in observed and unit not in missing_units and not unlocated and kind != 'unknown' else 'unknown'
            result.append(CoverageRecord(**base, stage='extraction', state=state,
                reason='POSITIONED_EVIDENCE_VALIDATED' if state == 'verified' else 'POSITION_OR_UNIT_KIND_MISSING',
                adapter_versions=adapters, extraction_methods=sorted(methods.get(unit, ()))))
            semantic_state, reason = 'unknown', 'PER_UNIT_SEMANTIC_COMMIT_MISSING'
            if 'model' in runtime and runtime['model'] is None:
                semantic_state, reason = 'partial_failed', 'EXTRACTIVE_ONLY'
            if cache:
                committed = cached_units[unit]
                graph = committed.analysis.tcm_graph
                if graph is not None and policy.semantic_version is not None and graph.semantic_version != policy.semantic_version:
                    raise ValueError('Graph version differs from runtime')
                if graph is not None and graph.nodes and state == 'verified':
                    semantic_state, reason = 'verified', 'PER_UNIT_SEMANTIC_CANDIDATE_VALIDATED_UNREVIEWED'
                elif graph is not None:
                    semantic_state, reason = 'partial_failed', 'NO_VALID_SEMANTIC_NODES_OR_POSITION'
                elif runtime.get('model') is None:
                    # Known absence differs from unknown old-package coverage: plan semantic only.
                    semantic_state, reason = 'partial_failed', 'EXTRACTIVE_ONLY'
            semantic_base = dict(base)
            semantic_base['integrity_basis'] = common['integrity_basis'] + (['ownership_per_unit_commit_validated'] if cache else [])
            if cache:
                semantic_base['address'] = address.model_copy(update={'resources': address.resources + ['ownership.json'] +
                    (['tcm.json'] if (path / 'tcm.json').exists() else [])})
            result.append(CoverageRecord(**semantic_base, stage='semantic_candidate', state=semantic_state,
                reason=reason, policy=policy))
        return result

    def plan(self, request: CoverageRequest | dict) -> CoveragePlan:
        request = CoverageRequest.model_validate(request)
        inventory = self.inventory()
        for item in request.history:
            inventory.records.append(CoverageRecord(source_sha256=item.source_sha256,
                unit_kind=item.unit_kind, units=item.units, stage=item.stage,
                state='historical_pending' if item.source_sha256 and item.units and item.unit_kind != 'unknown' else 'unknown',
                reason='DECLARED_NOT_RESTORED', history_reference=item.reference))
        inventory.records = _unique(inventory.records)
        records = inventory.records
        unresolved = [i for i, r in enumerate(records) if r.source_sha256 is None or r.unit_kind == 'unknown' or not r.units]
        target_records = [(i, r) for i, r in enumerate(records) if r.source_sha256 == request.source_sha256]
        conflicts = [(i, r) for i, r in target_records
            if r.unit_kind not in {'unknown', request.unit_kind} or
               (r.document_unit_count is not None and r.document_unit_count != request.document_unit_count) or
               any(u > request.document_unit_count for u in r.units)]
        by_unit, wildcard, lanes = {}, [], {}
        wanted = set(request.units)
        for i, r in target_records:
            if not r.units:
                wildcard.append((i, r))
            for unit in r.units:
                if unit in wanted:
                    by_unit.setdefault(unit, []).append((i, r))
            if r.state == 'verified' and r.address and r.address.active and r.address.family:
                lanes.setdefault((r.stage, r.address.family), set()).add((r.address.package_id, r.address.manifest_sha256))
        conflict_lanes = {key for key, ids in lanes.items() if len(ids) > 1}
        decisions = []
        for unit in request.units:
            relevant = by_unit.get(unit, []) + wildcard
            action, stage, reason, refs = 'covered', None, 'ALL_STAGES_VALIDATED_UNREVIEWED', []
            if conflicts:
                action, reason, refs = 'needs_check', 'UNIT_KIND_OR_DOCUMENT_SIZE_CONFLICT', [i for i, _ in conflicts]
            else:
                for current in STAGES:
                    matching = [(i, r) for i, r in relevant if r.stage == current]
                    verified = [(i, r) for i, r in matching if r.state == 'verified' and r.address and r.address.active]
                    if any((current, r.address.family) in conflict_lanes for _, r in verified):
                        action, stage, reason = 'needs_check', current, 'ACTIVE_REVISION_CONFLICT'
                        refs.extend(i for i, _ in verified)
                        break
                    if verified:
                        if current == 'semantic_candidate':
                            compatible, unknown = [], []
                            for i, r in verified:
                                expected, actual = request.policy.model_dump(), r.policy.model_dump()
                                keys = [k for k, v in expected.items() if v is not None]
                                if not keys or any(actual[k] is None for k in keys):
                                    unknown.append(i)
                                elif all(actual[k] == expected[k] for k in keys):
                                    compatible.append(i)
                            if not compatible:
                                action, stage, reason = 'needs_check', current, ('POLICY_UNKNOWN' if unknown else 'INCOMPATIBLE_POLICY')
                                refs.extend(i for i, _ in verified)
                                break
                            refs.extend(compatible)
                        else:
                            refs.extend(i for i, _ in verified)
                        continue
                    pending = [(i, r) for i, r in relevant if r.state == 'historical_pending' or
                               (r.state == 'verified' and r.address and not r.address.active)]
                    uncertain = [(i, r) for i, r in matching if r.state == 'unknown' or
                                 (r.state == 'partial_failed' and r.reason != 'EXTRACTIVE_ONLY')]
                    if uncertain:
                        action, stage, reason = 'needs_check', current, 'COVERAGE_UNKNOWN_OR_PARTIAL'
                        refs.extend(i for i, _ in uncertain)
                    elif pending:
                        action, stage, reason = 'held', current, 'HISTORY_PENDING_OR_INACTIVE'
                        refs.extend(i for i, _ in pending)
                    elif inventory.issues:
                        action, stage, reason = 'needs_check', current, 'UNRESOLVED_INPUTS_NOT_PROOF_OF_MISSING_COVERAGE'
                    else:
                        action, stage, reason = 'proposed', current, 'EARLIEST_MISSING_STAGE_ONLY'
                    break
            decisions.append(CoverageDecision(unit=unit, action=action, stage=stage, reason=reason,
                record_indexes=sorted(set(refs))))
        return CoveragePlan(source_sha256=request.source_sha256, unit_kind=request.unit_kind,
            document_unit_count=request.document_unit_count, policy=request.policy, inventory=inventory,
            decisions=decisions, unresolved_record_indexes=unresolved)
