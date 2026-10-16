from __future__ import annotations

import json
import os
import shutil
import time
from pathlib import Path
from uuid import uuid4

from medicine_agent.analysis.catalog import PackageCatalog
from medicine_agent.analysis.classification import classify
from medicine_agent.analysis.documents import adapter_versions, inspect_document
from medicine_agent.analysis.models import AnalysisError, AnalysisRequest, DocumentUnit, TaskCheckpoint
from medicine_agent.analysis.store import JobStore, digest, encoded, process_lock
from medicine_agent.bootstrap import create_facade
from medicine_agent.domain.ids import file_sha256, stable_id
from medicine_agent.domain.models import DocumentFragment, EvidenceRecord, SkillInvocation, SourceDocument
from medicine_agent.packages.io import validate_package_path
from medicine_agent.semantics import load_semantic_registry
from medicine_agent.runtime.files import replace_path
from medicine_agent.domain.owned_analysis import OwnedAnalysisRequest
from medicine_agent.packages.owned import read_owned_cache, analysis_options, attach_owned_cache, unit_records


class DataAnalysisAgent:
    """Constrained product agent: durable child task, allowlisted tools, checked output."""
    TOOLS = {"document-extraction": "0.1.0", "knowledge-distillation": "0.1.0",
             "tcm-knowledge-analysis": "0.2.0",
             "knowledge-package-build-validate": "0.1.0"}

    def __init__(self, workspace: Path, package_root: Path | None = None, model_client=None, *, branch_id=None):
        self.store = JobStore(workspace)
        settings = self.store.root / "settings.json"
        if package_root is not None:
            from medicine_agent.analysis.store import atomic_json
            relative = os.path.relpath(Path(package_root).resolve(), self.store.root)
            atomic_json(settings, {"package_root": relative, 'branch_id':branch_id})
        if not settings.exists():
            raise AnalysisError("PACKAGE_ROOT_REQUIRED", "Configure a package root for this workspace")
        configuration = json.loads(settings.read_text('utf-8'))
        configured = configuration['package_root']
        self.branch_id = configuration.get('branch_id')
        self.catalog = PackageCatalog(self.store.root / configured)
        self.facade = create_facade(model_client)
        self.model_client = model_client

    def _runtime(self, mode):
        model = None
        if mode == "model":
            if self.model_client is None or self.model_client.provider == "fake":
                raise AnalysisError("MODEL_CONFIG_MISSING", "Configure a real model or select extractive mode")
            model = {"provider": self.model_client.provider, "model": self.model_client.model}
            config = getattr(self.model_client, "config", None)
            if config:
                model["endpoint_fingerprint"] = digest(config.base_url)
        return {"contract": "t02p-0.2.0", "semantics": load_semantic_registry().version,
                "adapters": adapter_versions(), "tools": self.TOOLS, "model": model,
                "context_policy": "previous-unit-plus-current-v1", "analysis_policy": "source-faithfulness-v2"}

    def upgrade_unanalyzed_task(self, task):
        """Explicitly reuse only verified OCR when no analysis was committed."""
        with process_lock(self.store.task_dir(task) / 'run.lock'):
            row = self.store.get(task)
            data = json.loads(row['request'])
            if row['parent'] is None or any(r['analysis'] for r in self.store.rows(task)):
                raise AnalysisError('ANALYSIS_UPGRADE_UNSAFE', 'Upgrade only an unanalyzed child task')
            old, current = data['runtime'], self._runtime(data['request']['mode'])
            compatible = dict(old)
            compatible['analysis_policy'] = current['analysis_policy']
            if compatible != current:
                raise AnalysisError('CHECKPOINT_VERSION_CONFLICT', 'Other runtime changes require a new task')
            source = self.store.task_dir(task) / data['input']
            if (not source.is_file() or not source.resolve().is_relative_to(self.store.task_dir(task).resolve()) or
                    file_sha256(source.read_bytes()) != data['sha256']):
                raise AnalysisError('SOURCE_CHANGED', 'Cannot reuse OCR for changed input')
            self.store.recover(task)
            data['runtime'] = current
            self.store.update(task, request=encoded(data))
            self.store.record(task, {'event': 'analysis_policy_upgrade',
                'from_policy': old.get('analysis_policy'), 'to_policy': current['analysis_policy'],
                'reused_extraction_units': [r['ordinal'] for r in self.store.rows(task) if r['extraction']]})
        return self.status(task)

    def _invoke(self, task, skill, payload):
        if skill not in self.TOOLS:
            raise AnalysisError("TOOL_NOT_ALLOWED", "Tool is not allowed for data analysis")
        manifest = self.facade.registry.resolve(skill, self.TOOLS[skill]).manifest
        if manifest.status != "available":
            raise AnalysisError("TOOL_UNAVAILABLE", "Tool has not been enabled")
        result = self.facade.invoke_skill(SkillInvocation(task_id=task, skill_id=skill,
            skill_version=self.TOOLS[skill], caller="data-analysis-agent", input_data=payload))
        self.store.record(task, self.facade.get_run(result.invocation_id).model_dump(mode="json"))
        if result.status != "success" or result.output is None:
            issue = result.issues[0] if result.issues else None
            raise AnalysisError(issue.code if issue else "TOOL_FAILED",
                                issue.message if issue else "Tool failed")
        return result.output

    def submit(self, request: AnalysisRequest):
        # Orchestration is a distinct durable task. Each file gets an isolated child.
        request = OwnedAnalysisRequest.model_validate(request.model_dump(mode='json') if isinstance(request, AnalysisRequest) else request)
        self._runtime(request.mode)
        if request.parent_package and len(request.paths) != 1:
            raise AnalysisError("PARENT_SCOPE_INVALID", "One parent revision can update only one source")
        parent = "job_" + uuid4().hex
        prepared = []
        for source_path in request.paths:
            path = Path(source_path).resolve()
            fmt, count = inspect_document(path)
            if count == 0:
                raise AnalysisError("EMPTY_DOCUMENT", "Document has no units")
            units = sorted(set(request.units or range(1, count + 1)))
            if not units or units[0] < 1 or units[-1] > count:
                raise AnalysisError("UNIT_RANGE_INVALID", "Requested units are outside the document")
            child = "analysis_" + uuid4().hex
            directory = self.store.task_dir(child)
            directory.mkdir()
            snapshot = directory / ("input" + path.suffix.lower())
            shutil.copyfile(path, snapshot)
            sha = file_sha256(snapshot.read_bytes())
            source_id = stable_id("src", {"sha256": sha})
            family = stable_id("family", {"source_id": source_id, **({'owner_id':request.owner_id} if request.owner_id else {}),
                **({'derivation_id':self.branch_id} if self.branch_id else {})})
            cached, prior = None, None
            if request.parent_package:
                p = self.catalog._path(request.parent_package)
                if not validate_package_path(p).valid:
                    raise AnalysisError("PARENT_REVISION_INVALID", "Parent package failed validation")
                prior = json.loads((p / "revision.json").read_text("utf-8"))
                cached = read_owned_cache(p)
                # Contributor identity is provenance, never permission to continue learning.
                if cached and request.owner_id is None:
                    request = request.model_copy(update={'owner_id':cached.owner_id})
                    family = prior['family']
                if request.owner_id and (p/'corrections.json').exists():
                    raise AnalysisError('INCREMENTAL_CORRECTED_PARENT_UNSUPPORTED',
                        'Corrected parent cannot reuse pre-correction analysis; analyze new material independently')
                if prior["source_sha256"] != sha:
                    raise AnalysisError("PARENT_SOURCE_CONFLICT", "Parent is a different source file")
                # An update adds/reanalyzes scope; it cannot silently remove prior evidence.
                units = sorted(set(units) | set(prior["units"]))
            data = {"request": request.model_dump(mode="json", exclude={"paths"}),
                "input": snapshot.name, "file_name": path.name, "format": fmt,
                "sha256": sha, "source_id": source_id, "family": family, "units": units,
                "document_unit_count": count,
                "runtime": self._runtime(request.mode)}
            if self.branch_id:data['derivation_id']=self.branch_id
            if prior:
                data['revision_parent'] = request.parent_package if prior['family']==family else None
            if request.owner_id:
                data['reuse'] = {'parent_package_id': None, 'analysis_units': [],
                                 'extraction_units': [], 'invalidated_context_units': []}
                if cached:
                    if cached.runtime != data['runtime'] or cached.options_fingerprint != analysis_options(data['request']):
                        raise AnalysisError('INCREMENTAL_CONFIG_CONFLICT', 'Analysis configuration differs; do not silently mix cached outputs')
                    if cached.document_unit_count != count:
                        raise AnalysisError('SOURCE_CHANGED', 'Document structure differs from the parent cache')
                    data['reuse']['parent_package_id'] = json.loads((p/'manifest.json').read_text('utf-8'))['package_id']
                    data['cached_units'] = []
                    for unit in cached.units:
                        same_context = unit.predecessor_unit == (unit.ordinal-1 if unit.ordinal-1 in units else None)
                        data['cached_units'].append({'ordinal':unit.ordinal,
                            'extraction':unit.extraction.model_dump(mode='json'),
                            'analysis':unit.analysis.model_dump(mode='json') if same_context else None})
                        data['reuse']['extraction_units'].append(unit.ordinal)
                        data['reuse']['analysis_units' if same_context else 'invalidated_context_units'].append(unit.ordinal)
                    data['inherited_runs'] = [json.loads(line) for line in (p/'runs.jsonl').read_text('utf-8').splitlines() if line.strip()]
            prepared.append((child, data))
        with self.store.connect() as db:
            db.execute("INSERT INTO tasks(id,parent,status,request) VALUES (?,NULL,'queued',?)",
                       (parent, encoded({"role": "orchestrator", "children": [i[0] for i in prepared]})))
            for child, data in prepared:
                db.execute("INSERT INTO tasks(id,parent,status,request) VALUES (?,?,'queued',?)",
                           (child, parent, encoded(data)))
                db.executemany("INSERT INTO units(task,ordinal) VALUES (?,?)",
                               [(child, i) for i in data["units"]])
                for cached_unit in data.get('cached_units', []):
                    extraction, analysis = cached_unit['extraction'], cached_unit['analysis']
                    db.execute('UPDATE units SET extraction=?,extraction_hash=?,analysis=?,analysis_hash=? WHERE task=? AND ordinal=?',
                        (encoded(extraction),digest(extraction),encoded(analysis) if analysis is not None else None,
                         digest(analysis) if analysis is not None else None,child,cached_unit['ordinal']))
                # Keep copied checkpoints once in SQLite, not duplicated in task metadata.
                data.pop('cached_units', None)
                db.execute('UPDATE tasks SET request=? WHERE id=?',(encoded(data),child))
        return self.status(parent)

    def status(self, task):
        row = self.store.get(task)
        if row["parent"] is None:
            return {"task_id": task, "role": "orchestrator", "status": row["status"],
                    "children": [self.status(i) for i in self.store.children(task)]}
        rows = self.store.rows(task)
        pending = [r["ordinal"] for r in rows if r["analysis"] is None]
        return TaskCheckpoint(task_id=task, parent_task_id=row["parent"],
            role="data-analysis-agent", status=row["status"], unit_count=len(rows),
            extracted=sum(bool(r["extraction"]) for r in rows),
            analyzed=sum(bool(r["analysis"]) for r in rows),
            next_unit=pending[0] if pending else None,
            package_path=json.loads(row["result"])["package_path"] if row["result"] else None,
            errors=json.loads(row["errors"])).model_dump(mode="json")

    def pause(self, task):
        row = self.store.get(task)
        targets = self.store.children(task) if row["parent"] is None else [task]
        for child in targets:
            state = self.store.get(child)["status"]
            if state != "completed":
                self.store.update(child, pause=1,
                    status="pausing" if state in {"running", "resuming"} else "paused")
        if row["parent"] is None:
            self.store.update(task, status="pausing")
        return self.status(task)

    def run(self, task, *, max_units=None, max_seconds=None, stop_after_extraction=False,
            rebind: Path | None = None):
        if max_units is not None and max_units < 1:
            raise AnalysisError("BUDGET_INVALID", "max_units must be positive")
        if max_seconds is not None and max_seconds <= 0:
            raise AnalysisError("BUDGET_INVALID", "max_seconds must be positive")
        row = self.store.get(task)
        targets = self.store.children(task) if row["parent"] is None else [task]
        # Parent lock prevents two dispatchers from racing over the same child set.
        with process_lock(self.store.task_dir(task) / "run.lock"):
            if row["parent"] is None:
                self.store.update(task, status="running")
            for child in targets:
                if child == task:
                    self._run_child(child, max_units, max_seconds, stop_after_extraction, rebind)
                else:
                    with process_lock(self.store.task_dir(child) / "run.lock"):
                        self._run_child(child, max_units, max_seconds, stop_after_extraction, rebind)
            parent = task if row["parent"] is None else row["parent"]
            states = [self.store.get(i)["status"] for i in self.store.children(parent)]
            state = "completed" if all(s == "completed" for s in states) else (
                "failed" if "failed" in states else "paused")
            self.store.update(parent, status=state)
        return self.status(task)

    def _run_child(self, task, max_units, max_seconds, stop_after_extraction, rebind):
        row = self.store.get(task)
        if row["status"] == "completed":
            return
        try:
            data = json.loads(row["request"])
            config = data["request"]
        except (ValueError, KeyError, TypeError):
            self.store.update(task, status="failed", errors=encoded([
                {"code": "CHECKPOINT_INVALID", "message": "Task metadata is corrupt"}]))
            return
        try:
            if data["runtime"] != self._runtime(config["mode"]):
                raise AnalysisError("CHECKPOINT_VERSION_CONFLICT", "Runtime/config changed; create a new task")
            source_path = self.store.task_dir(task) / data["input"]
            if not source_path.resolve().is_relative_to(self.store.task_dir(task).resolve()):
                raise AnalysisError("INPUT_PATH_INVALID", "Input snapshot escapes task directory")
            if rebind:
                if file_sha256(rebind.read_bytes()) != data["sha256"]:
                    raise AnalysisError("SOURCE_CHANGED", "Replacement input fingerprint differs")
                shutil.copyfile(rebind, source_path)
            if not source_path.exists() or file_sha256(source_path.read_bytes()) != data["sha256"]:
                raise AnalysisError("SOURCE_CHANGED", "Input snapshot is missing or has changed")
            self.store.recover(task)
            if data.get('reuse'):
                recovered = self.store.rows(task)
                data['reuse']['analysis_units'] = [n for n in data['reuse']['analysis_units']
                    if any(r['ordinal']==n and r['analysis'] for r in recovered)]
                data['reuse']['extraction_units'] = [n for n in data['reuse']['extraction_units']
                    if any(r['ordinal']==n and r['extraction'] for r in recovered)]
                self.store.update(task, request=encoded(data))
            self.store.update(task, status="running", pause=0, errors="[]")
            start, completed = time.monotonic(), 0
            previous = []
            for unit in self.store.rows(task):
                if unit["analysis"]:
                    previous = json.loads(unit["analysis"])["current_evidence"]
                    continue
                if self.store.get(task)["pause"] or (
                    max_units is not None and completed >= max_units) or (
                    max_seconds is not None and time.monotonic() - start >= max_seconds):
                    self.store.update(task, status="paused")
                    return
                if not unit["extraction"]:
                    extraction = self._retry(task, config, "document-extraction", {
                        "path": str(source_path), "unit": unit["ordinal"],
                        "force_ocr": config["force_ocr"], "timeout_seconds": config["timeout_seconds"]})
                    self.store.commit_stage(task, unit["ordinal"], "extraction", extraction)
                else:
                    extraction = json.loads(unit["extraction"])
                if stop_after_extraction or self.store.get(task)["pause"]:
                    self.store.update(task, status="paused")
                    return
                current, fragments = self._evidence(data, extraction)
                # Carry only actual evidence from an immediately adjacent unit.
                adjacent = previous if unit["ordinal"] - 1 in data["units"] else []
                context = list({e["evidence_id"]: e for e in adjacent + current}.values())
                if current and config['mode'] == 'model':
                    from medicine_agent.analysis.quality import layout_candidate
                    output = self._retry(task, config, 'tcm-knowledge-analysis', {'evidence': context,
                        'focus_evidence_ids': [e['evidence_id'] for e in current],
                        'layout_evidence_ids': [e['evidence_id'] for e in context
                            if layout_candidate(e, config['metadata'].get('title'))]})
                else:
                    output = self._retry(task, config, "knowledge-distillation", {
                        "evidence": context, "use_model": False,
                        "combine_evidence": True}) if current else {"knowledge": [], "relations": []}
                allowed = {e["evidence_id"] for e in context}
                for claim in output["knowledge"] + output.get("relations", []):
                    if not claim.get("evidence_refs") or not set(claim["evidence_refs"]) <= allowed:
                        raise AnalysisError("EVIDENCE_TRACE_BROKEN", "Model/tool used an unregistered reference")
                self.store.commit_stage(task, unit["ordinal"], "analysis", {
                    "current_evidence": current, "fragments": fragments,
                    "knowledge": output["knowledge"], "relations": output.get("relations", []),
                    "tcm_graph": output.get('graph'),
                    "warnings": extraction["warnings"]})
                previous = current
                completed += 1
            self._build(task, data)
        except Exception as exc:
            # No raw model response, file body, credentials or provider errors in status.
            code = exc.code if isinstance(exc, AnalysisError) else "ANALYSIS_FAILED"
            self.store.update(task, status="failed", errors=encoded([{"code": code,
                "message": str(exc) if isinstance(exc, AnalysisError) else "Analysis operation failed"}]))

    def _retry(self, task, config, skill, payload):
        for attempt in range(config["max_attempts"]):
            try:
                return self._invoke(task, skill, payload)
            except AnalysisError as exc:
                if exc.code not in {"MODEL_CALL_FAILED", "OUTPUT_SCHEMA_INVALID", "EXTRACTION_TIMEOUT"}:
                    raise
                if attempt + 1 == config["max_attempts"]:
                    raise

    @staticmethod
    def _evidence(data, extraction):
        return unit_records(data, extraction)

    def _build(self, task, data):
        with process_lock(self.catalog.root / (".publish-" + digest(data["family"]) + ".lock")):
            self._build_locked(task, data)

    def _build_locked(self, task, data):
        target = self.catalog.root / data["family"] / task
        if target.exists():
            revision_file = target / "revision.json"
            if not validate_package_path(target).valid or not revision_file.exists():
                raise AnalysisError("PACKAGE_INVALID", "Committed revision is invalid")
            revision = json.loads(revision_file.read_text("utf8"))
            if revision["task_id"] != task or revision["source_sha256"] != data["sha256"]:
                raise AnalysisError("REVISION_CONFLICT", "Committed revision belongs to another task")
            self.store.update(task, status="completed", result=encoded({
                "package_path": target.relative_to(self.catalog.root).as_posix()}))
            return
        evidence, fragments, knowledge, relations, warnings = {}, {}, {}, {}, set()
        medical_nodes, medical_gaps = {}, []
        for row in self.store.rows(task):
            if row["analysis"] is None:
                raise AnalysisError("TASK_INCOMPLETE", "Not all units have committed analysis")
            payload = json.loads(row["analysis"])
            for collection, key, accumulator in (("current_evidence", "evidence_id", evidence),
                ("fragments", "fragment_id", fragments), ("knowledge", "knowledge_id", knowledge),
                ("relations", "relation_id", relations)):
                accumulator.update({v[key]: v for v in payload[collection]})
            warnings.update(payload["warnings"])
            if payload.get('tcm_graph'):
                medical_nodes.update({n['node_id']: n for n in payload['tcm_graph']['nodes']})
                medical_gaps.extend(payload['tcm_graph']['gaps'])
        if not knowledge:
            raise AnalysisError("NO_KNOWLEDGE", "No analyzable text; no complete package was committed")
        source = SourceDocument(source_id=data["source_id"], file_name=data["file_name"],
            media_type={"pdf": "application/pdf", "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "png": "image/png", "jpeg": "image/jpeg"}.get(data["format"], "text/plain"),
            sha256=data["sha256"], metadata=data["request"]["metadata"])
        staging = self.catalog.root / (".pending-" + task)
        if staging.exists():
            if staging.resolve() != self.catalog.root / staging.name or staging.is_symlink():
                raise AnalysisError('PACKAGE_PATH_INVALID', 'Task staging directory must not be redirected')
            shutil.rmtree(staging)
        built = self._invoke(task, "knowledge-package-build-validate", {
            "output_root": str(staging), "source": source.model_dump(mode="json"),
            "fragments": list(fragments.values()), "evidence": list(evidence.values()),
            "knowledge": list(knowledge.values()), "relations": list(relations.values()),
            "runs": list({r['invocation_id']:r for r in data.get('inherited_runs', []) +
                [r for r in self.store.calls(task) if "input_schema_id" in r]}.values())})
        candidate = Path(built["package_path"])
        if data['request']['mode'] == 'model':
            from medicine_agent.domain.tcm_knowledge import TCMKnowledgeGraph
            from medicine_agent.packages.tcm import attach_graph
            attach_graph(candidate, TCMKnowledgeGraph(nodes=list(medical_nodes.values()), gaps=medical_gaps))
        prior_classification = None
        if data["request"]["parent_package"]:
            previous = self.catalog._path(data["request"]["parent_package"]) / "revision.json"
            prior_classification = json.loads(previous.read_text("utf8")).get("classification")
        classification = classify("\n".join(e["raw_text"] for e in evidence.values()),
            data["request"].get("classification", {}), prior_classification)
        classification['knowledge_categories'] = sorted(set(classification['knowledge_categories']) |
            {c for n in medical_nodes.values() for c in n['categories']})
        if medical_nodes:
            classification['medical_profiles'] = sorted(set(classification['medical_profiles']) | {'tcm'})
            classification['basis'].append('TCM node content categories; model candidates, not medical approval')
            if classification['status'] == 'unclassified':
                classification['status'] = 'candidate'
        if medical_gaps or any(n['gaps'] for n in medical_nodes.values()):
            warnings.add('医学分析存在未理解或未结构化片段，须查阅 tcm.json 中的 gaps')
        self.catalog.attach_revision(candidate, data["family"], task, data["sha256"], data["units"],
            parent=data.get('revision_parent',data["request"]["parent_package"]), warnings=sorted(warnings),
            allowed_use=data["request"]["allowed_use"], runtime=data["runtime"],
            scope={"selected_units": data["units"],
                   "document_unit_count": data.get("document_unit_count"),
                   "covers_document": len(data["units"]) == data.get("document_unit_count")},
            classification=classification)
        if data['request'].get('owner_id'):
            base_id = json.loads((candidate/'manifest.json').read_text('utf-8'))['package_id']
            reuse = data['reuse']
            attach_owned_cache(candidate, {
                'owner_id':data['request']['owner_id'], 'content_package_id':base_id,
                'derivation_id':data.get('derivation_id'),
                'source_sha256':data['sha256'], 'source_id':data['source_id'],
                'runtime':data['runtime'], 'options_fingerprint':analysis_options(data['request']),
                'document_unit_count':data['document_unit_count'],
                'units':[{'ordinal':r['ordinal'],
                    'predecessor_unit':r['ordinal']-1 if r['ordinal']-1 in data['units'] else None,
                    'extraction':json.loads(r['extraction']), 'analysis':json.loads(r['analysis'])}
                    for r in self.store.rows(task)],
                'reused_from_package_id':reuse['parent_package_id'],
                'reused_analysis_units':reuse['analysis_units'],
                'reused_extraction_units':reuse['extraction_units'],
                'invalidated_context_units':reuse['invalidated_context_units']})
        if not validate_package_path(candidate).valid:
            raise AnalysisError("PACKAGE_INVALID", "Built package failed final validation")
        first = next(iter(knowledge))
        if not self.facade.query_package(str(candidate), knowledge_id=first)["evidence"]:
            raise AnalysisError("EVIDENCE_TRACE_BROKEN", "Built package cannot trace its first claim")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            replace_path(candidate, target)
        elif not validate_package_path(target).valid:
            raise AnalysisError("PACKAGE_INVALID", "Existing committed revision is invalid")
        self.store.update(task, status="completed", result=encoded({
            "package_path": target.relative_to(self.catalog.root).as_posix()}))
