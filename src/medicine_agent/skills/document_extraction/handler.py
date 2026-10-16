from medicine_agent.analysis.documents import extract_unit
from medicine_agent.analysis.models import AnalysisError, DocumentUnit, ExtractionInput
from medicine_agent.runtime.base import manifest_path
from medicine_agent.runtime.errors import PlatformError
from medicine_agent.runtime.manifest import load_manifest


class DocumentExtractionSkill:
    manifest = load_manifest(manifest_path(__file__))
    input_model = ExtractionInput
    output_model = DocumentUnit

    def execute(self, value, context):
        try:
            return extract_unit(value.path, value.unit, value.force_ocr, value.timeout_seconds)
        except AnalysisError as exc:
            error = PlatformError(str(exc))
            error.code = exc.code
            raise error from exc
