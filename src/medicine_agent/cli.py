from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from medicine_agent.bootstrap import create_facade
from medicine_agent.domain.models import SkillInvocation
from medicine_agent.model_adapters import OpenAICompatibleModelClient, load_llm_config
from medicine_agent.pipeline import run_minimal_pipeline


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

    validate = subparsers.add_parser("validate-package", help="Validate a package")
    validate.add_argument("package_path", type=Path)

    query = subparsers.add_parser("query-package", help="Query and trace a package")
    query.add_argument("package_path", type=Path)
    query.add_argument("--knowledge-id")
    query.add_argument("--text")

    smoke = subparsers.add_parser("llm-smoke", help="Run an explicit live LLM smoke test")
    smoke.add_argument("--config", type=Path, default=Path("config/llm.local.toml"))
    return parser


def main() -> None:
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
        _print(
            run_minimal_pipeline(
                create_facade(model_client),
                input_path=args.input_path,
                output_root=args.output_root,
                use_model=args.live_model,
            )
        )
        return
    if args.command == "validate-package":
        _print(
            create_facade().invoke_skill(
                SkillInvocation(
                    task_id="cli-validate",
                    skill_id="quality-evaluation",
                    input_data={"package_path": str(args.package_path)},
                )
            )
        )
        return
    if args.command == "query-package":
        _print(
            create_facade().invoke_skill(
                SkillInvocation(
                    task_id="cli-query",
                    skill_id="knowledge-package-query",
                    input_data={
                        "package_path": str(args.package_path),
                        "knowledge_id": args.knowledge_id,
                        "text": args.text,
                    },
                )
            )
        )
        return
    if args.command == "llm-smoke":
        client = OpenAICompatibleModelClient(load_llm_config(args.config))
        result = client.generate_json(
            system="Return a JSON object with an ok boolean.",
            user="Connectivity check. Do not include secrets.",
            schema={"type": "object", "required": ["ok"]},
        )
        _print({"provider": client.provider, "model": client.model, "response": result})


if __name__ == "__main__":
    main()

