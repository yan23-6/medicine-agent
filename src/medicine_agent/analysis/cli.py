from pathlib import Path
import json
import sqlite3

from medicine_agent.analysis.catalog import PackageCatalog
from medicine_agent.analysis.documents import capabilities
from medicine_agent.analysis.models import AnalysisError, AnalysisRequest, PackageClassification
from medicine_agent.domain.models import SourceMetadata
from medicine_agent.analysis.service import DataAnalysisAgent
from medicine_agent.analysis.orchestrator import OrchestratorAgent
from medicine_agent.domain.owned_analysis import OwnedAnalysisRequest
from medicine_agent.domain.learning import LearningRequest
from medicine_agent.analysis.file_learning import FileLearningService
from medicine_agent.analysis.library import default_knowledge_root
from medicine_agent.bootstrap import create_facade
from medicine_agent.model_adapters import OpenAICompatibleModelClient, load_llm_config
from medicine_agent.runtime.errors import PlatformError


def add_commands(subparsers):
    parser = subparsers.add_parser("analyze", help="Native file analysis, durable tasks and portable packages")
    commands = parser.add_subparsers(dest="action", required=True)
    commands.add_parser("capabilities")
    coverage = commands.add_parser('coverage', help='Read-only source inventory and optional incremental plan')
    coverage.add_argument('--packages', type=Path, default=default_knowledge_root())
    coverage.add_argument('--workspace', type=Path, default=Path.home()/'MedicineAgent'/'coverage-cache')
    coverage.add_argument('--input-file', type=Path, help='CoverageRequest JSON; omit for inventory only')
    prepare = commands.add_parser('review-prepare', help='Read-only review material and quality-gate preparation')
    prepare.add_argument('--packages', type=Path, default=default_knowledge_root())
    prepare.add_argument('--workspace', type=Path, default=Path.home()/'MedicineAgent'/'review-preparation-cache')
    prepare.add_argument('--input-file', type=Path, help='ReviewPreparationRequest JSON; default all top-level medpkg files')
    prepare.add_argument('--output-dir', type=Path, help='New directory; never overwrite existing output or source files')
    submit = commands.add_parser("submit")
    submit.add_argument("paths", nargs="+", type=Path)
    submit.add_argument("--workspace", type=Path, default=Path.home()/'MedicineAgent'/'workspace')
    submit.add_argument("--packages", type=Path, default=default_knowledge_root())
    submit.add_argument("--allowed-use", required=True)
    submit.add_argument("--mode", choices=["model", "extractive"], default="model")
    submit.add_argument("--units", help="1-based units/ranges: 1-100,105")
    submit.add_argument("--force-ocr", action="store_true")
    submit.add_argument("--parent-package")
    submit.add_argument('--owner-id', help='Optional contributor declaration; never update permission')
    submit.add_argument('--base-package', action='append', default=[], help='Existing .medpkg base; repeat for multiple files')
    submit.add_argument("--subjects", default="", help="Comma-separated subjects/topics")
    submit.add_argument("--material-types", default="", help="Comma-separated source-content types")
    submit.add_argument("--profiles", default="common")
    submit.add_argument("--knowledge-layers", default="")
    submit.add_argument('--knowledge-categories', default='', help='Comma-separated TCM content categories')
    submit.add_argument("--metadata-file", type=Path, help="SourceMetadata JSON; unknown values are null")
    submit.add_argument("--config", type=Path, default=Path("config/llm.local.toml"))
    for name in ("run", "status", "pause", "calls", "upgrade-analysis"):
        cmd = commands.add_parser(name)
        cmd.add_argument("task_id")
        cmd.add_argument("--workspace", type=Path, default=Path.home()/'MedicineAgent'/'workspace')
        if name == "run":
            cmd.add_argument("--max-units", type=int)
            cmd.add_argument("--max-seconds", type=float)
            cmd.add_argument("--stop-after-extraction", action="store_true")
            cmd.add_argument("--rebind", type=Path)
            cmd.add_argument("--config", type=Path)
        if name == 'upgrade-analysis':
            cmd.add_argument('--config', type=Path, required=True)
    for name in ("packages", "query", "select", "link", "links", 'review-queue', 'review-record', 'reviews', 'revise'):
        cmd = commands.add_parser(name)
        cmd.add_argument("--packages", type=Path, default=default_knowledge_root())
        cmd.add_argument('--workspace',type=Path,default=Path.home()/'MedicineAgent'/'workspace')
        if name == "query":
            cmd.add_argument("--text")
            cmd.add_argument("--knowledge-id")
            cmd.add_argument("--subject")
            cmd.add_argument("--material-type")
            cmd.add_argument("--medical-profile")
            cmd.add_argument("--knowledge-layer")
            cmd.add_argument('--knowledge-category')
            cmd.add_argument('--knowledge-type')
            cmd.add_argument('--evidence-state')
            cmd.add_argument('--topic')
            cmd.add_argument('--tcm-layer')
            cmd.add_argument('--seed-file',type=Path,help='JSON array of {package_id,node_id}')
            cmd.add_argument('--max-hops',type=int,default=2)
            cmd.add_argument('--max-nodes',type=int,default=50)
        if name == 'link':
            cmd.add_argument('--input-file', required=True, type=Path,
                help='JSON: source/target {package_id,node_id}, relation, rationale')
        if name == 'review-queue':
            cmd.add_argument('--scope', choices=['node', 'fact', 'all'], default='node')
            cmd.add_argument('--output-file', type=Path)
            cmd.add_argument('--markdown-file', type=Path)
        if name in {'review-record', 'revise'}:
            cmd.add_argument('--input-file', required=True, type=Path)
        if name == "select":
            cmd.add_argument("relative_path")


def parse_units(value):
    if value is None:
        return None
    result = set()
    try:
        for part in value.split(","):
            if "-" in part:
                left, right = map(int, part.split("-"))
                if not 1 <= left <= right <= 100000:
                    raise ValueError()
                result.update(range(left, right + 1))
            else:
                number = int(part)
                if number < 1:
                    raise ValueError()
                result.add(number)
    except ValueError as exc:
        raise AnalysisError("UNIT_RANGE_INVALID", "Use positive units/ranges such as 1-100,105") from exc
    return sorted(result)


def execute(args):
    try:
        if args.action == "capabilities":
            return capabilities()
        if args.action == 'coverage':
            from medicine_agent.analysis.coverage import CoverageService
            from medicine_agent.domain.coverage import CoverageRequest
            try:
                request = CoverageRequest.model_validate_json(args.input_file.read_text('utf-8')) if args.input_file else None
            except (OSError, ValueError, TypeError) as exc:
                raise AnalysisError('COVERAGE_REQUEST_INVALID', 'Supply a valid coverage/0.1.0 request') from exc
            service = CoverageService(args.packages, args.workspace)
            return (service.plan(request) if request is not None else service.inventory()).model_dump(mode='json')
        if args.action == 'review-prepare':
            from medicine_agent.analysis.review_preparation import ReviewPreparationService
            from medicine_agent.domain.review_preparation import ReviewPreparationRequest
            try:
                request = ReviewPreparationRequest.model_validate_json(args.input_file.read_text('utf-8')) if args.input_file else ReviewPreparationRequest()
            except (OSError, ValueError, TypeError) as exc:
                raise AnalysisError('PREPARATION_REQUEST_INVALID', 'Supply a valid review-preparation/0.1.0 request') from exc
            service = ReviewPreparationService(args.packages, args.workspace)
            if args.output_dir:
                return service.export(args.output_dir, request).model_dump(mode='json')
            return service.prepare(request).model_dump(mode='json')
        if args.action in {"packages", "query", "select", "link", "links", 'review-queue', 'review-record', 'reviews', 'revise'}:
            public = bool(list(args.packages.glob('*.medpkg'))) or not list(args.packages.rglob('manifest.json'))
            files = FileLearningService(args.workspace,args.packages) if public else None
            catalog = files.library.view()[0] if files else PackageCatalog(args.packages)
            if args.action == "packages":
                if files:return {'packages':files.library.scan(),'selected':catalog.selected()}
                return {"packages": catalog.scan(), "selected": catalog.selected()}
            if args.action == "select":
                if files:return files.library.select(args.relative_path)
                return catalog.select(args.relative_path)
            if args.action == 'links':
                return catalog.associations()
            if args.action == 'link':
                if files:return files.associate(json.loads(args.input_file.read_text('utf-8')))
                return catalog.associate(**json.loads(args.input_file.read_text('utf-8')))
            if args.action == 'reviews':
                return catalog.reviews()
            if args.action == 'revise':
                if files:return files.revise(json.loads(args.input_file.read_text('utf-8')))
                return catalog.revise_candidate(json.loads(args.input_file.read_text('utf-8')))
            if args.action == 'review-record':
                if files:return files.record_review(json.loads(args.input_file.read_text('utf-8')))
                return catalog.record_review(json.loads(args.input_file.read_text('utf-8')))
            if args.action == 'review-queue':
                queue = catalog.review_queue(args.scope)
                if args.output_file or args.markdown_file:
                    from medicine_agent.analysis.store import atomic_json
                    for path,suffix in ((args.output_file,'.json'),(args.markdown_file,'.md')):
                        if path and (path.resolve().is_relative_to(catalog.root) or path.resolve().is_relative_to(args.packages.resolve()) or path.suffix.lower()!=suffix):
                            raise AnalysisError('REVIEW_EXPORT_PATH_INVALID', 'Export derived files outside the source package root')
                    if args.output_file:
                        atomic_json(args.output_file,queue)
                    if args.markdown_file:
                        from medicine_agent.analysis.reviews import render_review_markdown
                        args.markdown_file.parent.mkdir(parents=True,exist_ok=True)
                        args.markdown_file.write_text(render_review_markdown(queue),encoding='utf-8')
                    return {'output': str(args.output_file) if args.output_file else None,
                        'markdown':str(args.markdown_file) if args.markdown_file else None,
                        'count':len(queue['items']), 'errors':queue['errors']}
                return queue
            try:
                seeds=json.loads(args.seed_file.read_text('utf-8')) if args.seed_file else []
                from medicine_agent.domain.retrieval import LocalKnowledgeQuery
                query=LocalKnowledgeQuery(text=args.text,knowledge_id=args.knowledge_id,seed_addresses=seeds,
                    subject=args.subject,material_type=args.material_type,medical_profile=args.medical_profile,
                    knowledge_layer=args.knowledge_layer,knowledge_category=args.knowledge_category,
                    knowledge_type=args.knowledge_type,evidence_state=args.evidence_state,topic=args.topic,
                    tcm_layer=args.tcm_layer,max_hops=args.max_hops,max_nodes=args.max_nodes).model_dump(mode='json',exclude_none=True)
            except (OSError,ValueError,TypeError) as exc:
                raise AnalysisError('QUERY_INVALID','Supply a valid text, knowledge identity, or seed file and bounded filters') from exc
            if files:return files.query(**query)
            return catalog.query(create_facade(),**query)
        client = None
        if args.action == "submit" and args.mode == "model":
            client = OpenAICompatibleModelClient(load_llm_config(args.config))
        elif args.action in {"run", "upgrade-analysis"} and args.config is not None:
            client = OpenAICompatibleModelClient(load_llm_config(args.config))
        if args.action == "submit":
            categories = PackageClassification(subjects=split(args.subjects),
                knowledge_categories=split(args.knowledge_categories),
                material_types=split(args.material_types), medical_profiles=split(args.profiles),
                knowledge_layers=split(args.knowledge_layers))
            metadata = {}
            if args.metadata_file:
                try:
                    metadata = {"metadata": SourceMetadata.model_validate_json(args.metadata_file.read_text("utf8"))}
                except (OSError, ValueError) as exc:
                    raise AnalysisError("METADATA_INVALID", "Invalid source metadata file") from exc
            request = LearningRequest(paths=[str(p) for p in args.paths], owner_id=args.owner_id,base_packages=args.base_package,
                allowed_use=args.allowed_use, mode=args.mode, units=parse_units(args.units),
                force_ocr=args.force_ocr, parent_package=args.parent_package,
                classification=categories, **metadata)
            return OrchestratorAgent(args.workspace,args.packages,client).receive('analyze_files',request.model_dump(mode='json'))
        if args.task_id.startswith('learning_'):
            service=FileLearningService(args.workspace,model_client=client)
            if args.action=='run':return service.run(args.task_id,max_units=args.max_units,max_seconds=args.max_seconds,
                stop_after_extraction=args.stop_after_extraction,rebind=args.rebind)
            if args.action=='pause':return service.pause(args.task_id)
            if args.action=='calls':
                directory=service.task_dir(args.task_id)
                data=json.loads((directory/'task.json').read_text('utf-8'))
                core=DataAnalysisAgent(directory/'analysis',model_client=client)
                return [r for child in core.store.children(data['inner_task_id']) for r in core.store.calls(child)]
            if args.action=='upgrade-analysis':raise AnalysisError('ANALYSIS_UPGRADE_UNSAFE','Upgrade an unanalyzed child checkpoint, not a delivery task')
            return service.status(args.task_id)
        agent = DataAnalysisAgent(args.workspace, getattr(args, "packages", None), client)
        if args.action == "run":
            return agent.run(args.task_id, max_units=args.max_units, max_seconds=args.max_seconds,
                stop_after_extraction=args.stop_after_extraction, rebind=args.rebind)
        if args.action == 'upgrade-analysis':
            return agent.upgrade_unanalyzed_task(args.task_id)
        if args.action == "pause":
            return agent.pause(args.task_id)
        if args.action == "calls":
            return agent.store.calls(args.task_id)
        return agent.status(args.task_id)
    except AnalysisError as exc:
        error = PlatformError(str(exc))
        error.code = exc.code
        raise error from exc
    except (OSError, sqlite3.DatabaseError, json.JSONDecodeError) as exc:
        error = PlatformError("Unable to access analysis workspace or package catalog")
        error.code = "ANALYSIS_STORAGE_INVALID"
        raise error from exc


def split(value):
    return [item.strip() for item in value.split(",") if item.strip()]
