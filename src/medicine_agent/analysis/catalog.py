from __future__ import annotations

import json
from pathlib import Path

from medicine_agent.analysis.models import AnalysisError
from medicine_agent.analysis.models import PackageClassification, PackageRevision
from medicine_agent.analysis.store import atomic_json, digest, process_lock
from medicine_agent.domain.ids import file_sha256
from medicine_agent.packages.io import validate_package_path


class PackageCatalog:
    """Relative, rebuildable catalog over portable experimental packages."""
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, relative):
        path = (self.root / relative).resolve()
        if not path.is_relative_to(self.root):
            raise AnalysisError("PACKAGE_PATH_INVALID", "Package path escapes catalog root")
        return path

    def scan(self):
        items = []
        for manifest in sorted(self.root.rglob("manifest.json")):
            if any(p.startswith(".pending") for p in manifest.relative_to(self.root).parts):
                continue
            path = manifest.parent
            if not path.resolve().is_relative_to(self.root):
                continue
            item = {"path": path.relative_to(self.root).as_posix(), "state": "quarantined"}
            try:
                report = validate_package_path(path)
                data = json.loads(manifest.read_text("utf-8"))
                revision_file = path / "revision.json"
                revision = json.loads(revision_file.read_text("utf-8")) if revision_file.exists() else {}
                if revision:
                    revision = PackageRevision.model_validate(revision).model_dump(mode="json")
                if revision and "revision.json" not in data["files"]:
                    raise ValueError("Unprotected revision metadata")
                ownership = json.loads((path/'ownership.json').read_text('utf-8')) if 'ownership.json' in data['files'] else {}
                item.update({"package_id": data["package_id"],
                    'owner_id':ownership.get('owner_id'),
                    'analysis_reuse':{k:ownership[k] for k in ('reused_from_package_id','reused_analysis_units',
                        'reused_extraction_units','invalidated_context_units') if k in ownership},
                    "family": revision.get("family", data["package_id"]),
                    "sequence": revision.get("sequence", 0), "revision": revision,
                    "requires_explicit_selection": "corrections.json" in data["files"],
                    "classification": revision.get("classification", PackageClassification().model_dump()),
                    "state": "research_candidate" if report.valid else "quarantined",
                    "errors": [i.code for i in report.issues]})
            except (OSError, ValueError, KeyError, TypeError):
                item["errors"] = ["PACKAGE_INVALID"]
            items.append(item)
        return items

    def selected(self):
        pins_file = self.root / ".selected.json"
        pins = json.loads(pins_file.read_text("utf-8")) if pins_file.exists() else {}
        groups = {}
        for item in self.scan():
            if item["state"] != "quarantined":
                groups.setdefault(item["family"], []).append(item)
        selected = []
        for family, items in groups.items():
            if family in pins:
                found = [i for i in items if i["path"] == pins[family]]
                if not found:
                    raise AnalysisError("PIN_UNAVAILABLE", "Pinned package is missing or invalid")
                selected.append(found[0])
                continue
            items = [i for i in items if not i['requires_explicit_selection']]
            if not items:
                continue
            highest = max(i["sequence"] for i in items)
            candidates = [i for i in items if i["sequence"] == highest]
            # Exact copies may be deduplicated; conflicting identities must be selected explicitly.
            if len({i["package_id"] for i in candidates}) != 1:
                raise AnalysisError("REVISION_CONFLICT", "Conflicting package revisions require selection")
            selected.append(candidates[0])
        return selected

    def select(self, relative):
        self._path(relative)
        item = next((i for i in self.scan() if i["path"] == relative
                     and i["state"] != "quarantined"), None)
        if item is None:
            raise AnalysisError("PACKAGE_INVALID", "Cannot select missing or invalid package")
        with process_lock(self.root / ".selection.lock"):
            path = self.root / ".selected.json"
            pins = json.loads(path.read_text("utf-8")) if path.exists() else {}
            pins[item["family"]] = relative
            atomic_json(path, pins)
        return item

    def query(self, facade, text=None, knowledge_id=None, *, seed_addresses=(), subject=None, material_type=None,
              medical_profile=None, knowledge_layer=None, knowledge_category=None,
              knowledge_type=None, evidence_state=None, topic=None, tcm_layer=None,
              max_hops=2, max_nodes=50):
        results = []
        from medicine_agent.analysis.associations import node_index, related
        from medicine_agent.analysis.retrieval import derive_facets, matches_facets
        from medicine_agent.analysis.associations import address_key
        index = node_index(self)
        seed_keys = {address_key(a) for a in seed_addresses}
        addresses = []
        for item in self.selected():
            categories = item["classification"]
            if any(value and value not in categories[field] for field, value in (
                ("subjects", subject), ("material_types", material_type),
                ("medical_profiles", medical_profile), ("knowledge_layers", knowledge_layer))):
                continue
            item_seeds=sorted(nid for pid,nid in seed_keys if pid==item['package_id'])
            if not (text or knowledge_id or item_seeds):
                continue
            response = facade.query_package(str(self._path(item["path"])),
                                            text=text, knowledge_id=knowledge_id or (item_seeds[0] if item_seeds else None))
            # Rich text search includes facts, not just the legacy label/statement projection.
            import json
            matched = []
            for (pid,nid),record in index.items():
                if pid != item['package_id']:
                    continue
                selected_by_seed=(pid,nid) in seed_keys
                selected_by_query=bool(knowledge_id or text) and (not knowledge_id or nid==knowledge_id) and (
                    not text or text.casefold() in json.dumps(record['node'],ensure_ascii=False).casefold())
                facets=derive_facets(record['node'],record['package'])
                if not (selected_by_seed or selected_by_query):continue
                if knowledge_category and knowledge_category not in record['node']['categories']:continue
                if not matches_facets(facets,knowledge_type=knowledge_type,evidence_state=evidence_state,
                                      topic=topic,tcm_layer=tcm_layer):continue
                matched.append({**record,'facets':facets})
            response['medical_nodes'] = [{**record['node'],'retrieval_facets':record['facets']} for record in matched]
            if any((knowledge_category,knowledge_type,evidence_state,topic,tcm_layer)) and not matched:
                continue
            if knowledge_category:
                ids = {record['node']['node_id'] for record in matched}
                response['matches'] = [m for m in response.get('matches', []) if m['knowledge_id'] in ids]
                if not matched:
                    continue
            # Return the full source records for medical fields found outside the base summary.
            response['medical_evidence'] = list({e['evidence_id']: e for record in matched for e in record['evidence']}.values())
            response['medical_sources'] = list({e['source_id']: e for record in matched for e in record['sources']}.values())
            graph_path = self._path(item['path']) / 'tcm.json'
            if graph_path.exists():
                from medicine_agent.analysis.quality import quality_view
                from medicine_agent.packages.io import read_jsonl
                records = read_jsonl(graph_path.parent / 'evidence.jsonl')
                source_records = read_jsonl(graph_path.parent / 'sources.jsonl')
                title = source_records[0].get('metadata', {}).get('title') if source_records else None
                response['analysis_quality'] = quality_view(json.loads(graph_path.read_text('utf-8')), records, title)
            from medicine_agent.packages.corrections import read_corrections
            correction = read_corrections(self._path(item['path']))
            response['correction_provenance'] = correction.model_dump(mode='json') if correction else None
            addresses.extend(record['address'] for record in matched)
            results.append({"package": item, **response})
        from medicine_agent.analysis.reviews import read_reviews
        linked = related(self, [*addresses,*seed_addresses], index,max_hops=max_hops,max_nodes=max_nodes)
        visible = {address_key(a) for a in addresses}
        visible.update(address_key(n['address']) for n in linked['related_nodes'])
        reviews = read_reviews(self, index)
        from medicine_agent.analysis.concepts import concept_groups, concept_candidates
        active_ids={p['package_id'] for p in self.selected()}
        groups=concept_groups({k:v for k,v in index.items() if k[0] in active_ids})
        candidate_index={k:v for k,v in index.items() if k[0] in active_ids}
        linked_pairs={tuple(sorted((address_key(e['source']),address_key(e['target'])))) for e in linked['associations']}
        candidates=concept_candidates(candidate_index,{address_key(a) for a in addresses},excluded=linked_pairs)
        local_records=[]
        traversed={address_key(a) for a in linked['traversal']['visited_addresses']}
        for address in addresses:
            key=address_key(address)
            if key in index and key in traversed:local_records.append((index[key],'seed'))
        for record in linked['related_nodes']:local_records.append((record,'related'))
        seen=set();local_nodes=[]
        for record,role in local_records:
            key=address_key(record['address'])
            if key in seen:continue
            seen.add(key)
            local_nodes.append({'address':record['address'],'title':record['node']['title'],
                'statement':record['node']['statement'],'facets':derive_facets(record['node'],record['package']),'role':role})
        from medicine_agent.domain.retrieval import LocalKnowledgeGraph
        graph=LocalKnowledgeGraph.model_validate({'nodes':local_nodes,
            'edges':[{k:edge[k] for k in ('association_id','source','target','relation','rationale','status','resolution')}
                     for edge in linked['associations']],
            'audit':{'requested_max_hops':max_hops,'requested_max_nodes':max_nodes,
                'visited_nodes':linked['traversal']['visited_nodes'],'traversed_edges':linked['traversal']['traversed_edges'],
                'truncated':linked['traversal']['truncated'],
                'missing_seed_addresses':linked['traversal']['missing_seed_addresses'],
                'filters':{k:v for k,v in {'subject':subject,'material_type':material_type,
                    'medical_profile':medical_profile,'knowledge_layer':knowledge_layer,
                    'knowledge_category':knowledge_category,'knowledge_type':knowledge_type,
                    'evidence_state':evidence_state,'topic':topic,'tcm_layer':tcm_layer}.items() if v is not None}}})
        return {"status": "research_candidate", "packages": results,
                'concept_groups':[{**g,'source_records':[index[address_key(a)] for a in g['members']]}
                    for g in groups if any(address_key(a) in visible for a in g['members'])],
                "medical_review": "unreviewed", "consultation_available": False,
                'user_reviews': [r for r in reviews['records'] if address_key(r['request']['target']['address']) in visible],
                'user_review_states': [s for s in reviews['states'].values() if address_key(s['target']['address']) in visible],
                'review_errors': reviews['errors'],'local_graph':graph.model_dump(mode='json'),
                'concept_link_candidates':candidates, **linked}

    def associate(self, source, target, relation, rationale):
        from medicine_agent.analysis.associations import associate
        return associate(self, source, target, relation, rationale)

    def associations(self):
        from medicine_agent.analysis.associations import read_associations
        return read_associations(self)

    def review_queue(self, scope='node'):
        from medicine_agent.analysis.reviews import review_queue
        return review_queue(self, scope)

    def record_review(self, request):
        from medicine_agent.analysis.reviews import record_review
        return record_review(self, request)

    def reviews(self):
        from medicine_agent.analysis.reviews import read_reviews
        return read_reviews(self)

    def revise_candidate(self, request):
        from medicine_agent.analysis.corrections import revise_candidate
        return revise_candidate(self, request)

    def attach_revision(self, path, family, task, source_sha, units, parent=None, warnings=None,
                        allowed_use=None, runtime=None, scope=None, classification=None):
        path = Path(path)
        with process_lock(self.root / (".family-" + digest(family) + ".lock")):
            existing_file = path / "revision.json"
            if existing_file.exists():
                existing = json.loads(existing_file.read_text("utf-8"))
                if (existing["task_id"] == task and existing["source_sha256"] == source_sha
                    and existing["units"] == units and existing["family"] == family):
                    # Recover a crash between revision write and manifest checksum commit.
                    manifest = json.loads((path / "manifest.json").read_text("utf8"))
                    expected = file_sha256(existing_file.read_bytes())
                    if "revision.json" not in manifest["files"]:
                        manifest["files"]["revision.json"] = expected
                        atomic_json(path / "manifest.json", manifest)
                        atomic_json(path / "checksums.json", manifest["files"])
                    elif manifest["files"]["revision.json"] != expected:
                        raise AnalysisError("PACKAGE_INVALID", "Revision metadata checksum differs")
                    return existing
                raise AnalysisError("REVISION_CONFLICT", "Output revision already belongs to another task")
            previous = None
            if parent:
                parent_path = self._path(parent)
                if not validate_package_path(parent_path).valid:
                    raise AnalysisError("PARENT_REVISION_INVALID", "Parent package is not valid")
                previous = json.loads((parent_path / "revision.json").read_text("utf-8"))
                if previous["family"] != family or previous["source_sha256"] != source_sha:
                    raise AnalysisError("PARENT_SOURCE_CONFLICT", "Parent refers to a different source")
                current = [i for i in self.selected() if i["family"] == family]
                if current and current[0]["path"] != parent:
                    raise AnalysisError("PARENT_REVISION_CONFLICT", "Parent is no longer the selected revision")
            else:
                if any(i["family"] == family and i["path"] != path.relative_to(self.root).as_posix()
                       for i in self.scan() if i["state"] != "quarantined"):
                    raise AnalysisError("PARENT_REVISION_REQUIRED", "Existing source requires an explicit parent")
            revision = {"family": family, "task_id": task, "source_sha256": source_sha,
                "parent": previous["task_id"] if previous else None,
                "sequence": previous["sequence"] + 1 if previous else 1,
                "units": units, "review_status": "unreviewed", "warnings": warnings or [],
                "allowed_use": allowed_use, "runtime": runtime,
                "processing_scope": scope,
                "classification": classification or PackageClassification().model_dump(mode="json"),
                "changes": {"added_units": sorted(set(units) - set(previous["units"] if previous else [])),
                            "removed_units": sorted(set(previous["units"] if previous else []) - set(units))}}
            revision = PackageRevision.model_validate(revision).model_dump(mode="json")
            atomic_json(existing_file, revision)
            manifest = json.loads((path / "manifest.json").read_text("utf-8"))
            manifest["files"]["revision.json"] = file_sha256(existing_file.read_bytes())
            atomic_json(path / "manifest.json", manifest)
            atomic_json(path / "checksums.json", manifest["files"])
            return revision
