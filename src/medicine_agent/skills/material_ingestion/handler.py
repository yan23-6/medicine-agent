from __future__ import annotations

from pathlib import Path

from medicine_agent.domain.ids import file_sha256, stable_id
from medicine_agent.domain.models import DocumentFragment, SourceDocument
from medicine_agent.runtime.base import SkillContext, manifest_path
from medicine_agent.runtime.errors import PlatformError, UnsupportedFormatError
from medicine_agent.runtime.manifest import load_manifest
from medicine_agent.skills.material_ingestion.models import (
    MaterialIngestionInput,
    MaterialIngestionOutput,
)


class MaterialIngestionSkill:
    manifest = load_manifest(manifest_path(__file__))
    input_model = MaterialIngestionInput
    output_model = MaterialIngestionOutput

    def execute(
        self, value: MaterialIngestionInput, context: SkillContext
    ) -> MaterialIngestionOutput:
        del context
        path = Path(value.path).resolve()
        if path.suffix.lower() not in {".md", ".txt"}:
            raise UnsupportedFormatError(f"Unsupported file format: {path.suffix}")
        try:
            data = path.read_bytes()
            text = data.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            raise PlatformError(f"Unable to read UTF-8 input: {path.name}") from exc
        digest = file_sha256(data)
        source_id = stable_id("src", {"sha256": digest, "name": path.name})
        source = SourceDocument(
            source_id=source_id,
            file_name=path.name,
            media_type="text/markdown" if path.suffix.lower() == ".md" else "text/plain",
            sha256=digest,
            metadata=value.metadata,
        )
        fragments: list[DocumentFragment] = []
        current: list[str] = []
        start_line = 1
        lines = text.splitlines()

        def flush(end_line: int) -> None:
            nonlocal current, start_line
            paragraph = "\n".join(current).strip()
            if paragraph:
                ordinal = len(fragments)
                fragments.append(
                    DocumentFragment(
                        fragment_id=stable_id(
                            "frag",
                            {
                                "source_id": source_id,
                                "ordinal": ordinal,
                                "text": paragraph,
                            },
                        ),
                        source_id=source_id,
                        ordinal=ordinal,
                        text=paragraph,
                        start_line=start_line,
                        end_line=end_line,
                    )
                )
            current = []

        for line_number, line in enumerate(lines, start=1):
            if line.strip():
                if not current:
                    start_line = line_number
                current.append(line)
            else:
                flush(line_number - 1)
        flush(len(lines))
        return MaterialIngestionOutput(source=source, fragments=fragments)

