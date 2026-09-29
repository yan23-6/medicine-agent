from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, ValidationError

from medicine_agent.bootstrap import create_facade
from medicine_agent.contracts import export_schemas
from medicine_agent.domain.models import SkillInvocation
from medicine_agent.model_adapters import OpenAICompatibleModelClient, load_llm_config
from medicine_agent.pipeline import run_minimal_pipeline
from medicine_agent.runtime.errors import PlatformError, SemanticContractError
from medicine_agent.semantics import validate_semantic_registry


class SmokeResponse(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    ok: bool


def _print(value: Any) -> None:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    print(json.dumps(value, ensure_ascii=False, indent=2, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="medicine-agent")
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("list-skills", help="List registered skills")

    describe = subparsers.add_parser("describe-skill", help="Show manifest and schemas")
    describe.add_argument("skill_id")
    describe.add_argument("--version")

    invoke = subparsers.add_parser("invoke", help="Invoke a skill from a JSON input file")
    invoke.add_argument("skill_id")
    invoke.add_argument("--input-file", type=Path, required=True)
    invoke.add_argument("--version")

    pipeline = subparsers.add_parser("pipeline", help="Run the minimal package round trip")
    pipeline.add_argument("input_path", type=Path)
    pipeline.add_argument("--output-root", type=Path, default=Path("artifacts/packages"))
    pipeline.add_argument("--live-model", action="store_true")
    pipeline.add_argument("--config", type=Path, default=Path("config/llm.local.toml"))
    pipeline.add_argument("--raw-fields-file", type=Path)
    pipeline.add_argument("--combine-evidence", action="store_true")

    validate = subparsers.add_parser("validate-package", help="Validate a package")
    validate.add_argument("package_path", type=Path)

    query = subparsers.add_parser("query-package", help="Query and trace a package")
    query.add_argument("package_path", type=Path)
    query.add_argument("--knowledge-id")
    query.add_argument("--text")

    trace = subparsers.add_parser("trace-evidence", help="Trace knowledge to evidence")
    trace.add_argument("package_path", type=Path)
    trace.add_argument("knowledge_id")

    schemas = subparsers.add_parser("export-schemas", help="Export versioned JSON Schemas")
    schemas.add_argument("--output-dir", type=Path, default=Path("schemas/t01"))
    schemas.add_argument("--contract-set", choices=["t01", "t02"], default="t01")

    subparsers.add_parser(
        "validate-semantics", help="Validate the unified semantic registry"
    )

    smoke = subparsers.add_parser("llm-smoke", help="Run an explicit live LLM smoke test")
    smoke.add_argument("--config", type=Path, default=Path("config/llm.local.toml"))
    return parser


def _main() -> None:
    args = build_parser().parse_args()
    if args.command == "list-skills":
        _print([item.model_dump(mode="json") for item in create_facade().list_skills()])
        return
    if args.command == "describe-skill":
        _print(create_facade().describe_skill(args.skill_id, args.version))
        return
    if args.command == "invoke":
        payload = json.loads(args.input_file.read_text(encoding="utf-8"))
        result = create_facade().invoke_skill(
            SkillInvocation(
                task_id="cli-invoke",
                skill_id=args.skill_id,
                skill_version=args.version,
                input_data=payload,
            )
        )
        _print(result)
        return
    if args.command == "pipeline":
        model_client = None
        if args.live_model:
            model_client = OpenAICompatibleModelClient(load_llm_config(args.config))
        raw_fields = None
        if args.raw_fields_file:
            raw_fields = json.loads(args.raw_fields_file.read_text(encoding="utf-8"))
            if not isinstance(raw_fields, list):
                raise ValueError("raw fields file must contain a JSON array")
        _print(
            run_minimal_pipeline(
                create_facade(model_client),
                input_path=args.input_path,
                output_root=args.output_root,
                use_model=args.live_model,
                raw_fields=raw_fields,
                combine_evidence=args.combine_evidence,
            )
        )
        return
    if args.command == "validate-package":
        _print(create_facade().validate_package(str(args.package_path)))
        return
    if args.command == "query-package":
        _print(
            create_facade().query_package(
                str(args.package_path),
                knowledge_id=args.knowledge_id,
                text=args.text,
            )
        )
        return
    if args.command == "trace-evidence":
        _print(
            create_facade().trace_evidence(
                str(args.package_path),
                args.knowledge_id,
            )
        )
        return
    if args.command == "export-schemas":
        _print(
            export_schemas(
                create_facade(), args.output_dir, contract_set=args.contract_set
            )
        )
        return
    if args.command == "validate-semantics":
        try:
            report = validate_semantic_registry()
        except ValidationError as exc:
            raise SemanticContractError(
                "Unified semantic registry validation failed",
                details={"errors": exc.errors(include_url=False)},
            ) from exc
        _print(report)
        return
    if args.command == "llm-smoke":
        client = OpenAICompatibleModelClient(load_llm_config(args.config))
        raw_result = client.generate_json(
            system="Return a JSON object with an ok boolean.",
            user="Connectivity check. Do not include secrets.",
            schema={"type": "object", "required": ["ok"]},
        )
        result = SmokeResponse.model_validate(raw_result)
        _print(
            {
                "provider": client.provider,
                "model": client.model,
                "schema_valid": True,
                "response": result,
            }
        )


def main() -> None:
    try:
        _main()
    except PlatformError as exc:
        _print(
            {
                "status": "failure",
                "error": {
                    "code": exc.code,
                    "message": exc.message,
                    "details": exc.details,
                },
            }
        )
        raise SystemExit(1) from None
    except ValidationError:
        _print(
            {
                "status": "failure",
                "error": {
                    "code": "OUTPUT_SCHEMA_INVALID",
                    "message": "Live model response failed the smoke-test schema",
                    "details": {},
                },
            }
        )
        raise SystemExit(1) from None


if __name__ == "__main__":
    main()

