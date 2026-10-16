from __future__ import annotations

import importlib.metadata
import io
import json
import subprocess
import sys
import zipfile
from contextlib import closing
from pathlib import Path

from medicine_agent.analysis.models import (
    AnalysisError, DocumentBlock, DocumentPosition, DocumentUnit,
)


def adapter_versions() -> dict[str, str]:
    return {name: importlib.metadata.version(name) for name in
            ("pypdfium2", "python-docx", "pillow", "rapidocr", "onnxruntime")}


def capabilities() -> dict:
    try:
        versions = adapter_versions()
        return {"formats": ["pdf", "docx", "txt", "md", "png", "jpeg"],
                "available": True, "versions": versions,
                "ocr": "local RapidOCR/ONNX CPU", "other_formats": "unsupported"}
    except importlib.metadata.PackageNotFoundError as exc:
        return {"available": False, "error": str(exc)}


def detect(path: Path) -> str:
    if not path.is_file():
        raise AnalysisError("INPUT_MISSING", "Input file is unavailable")
    with path.open("rb") as stream:
        head = stream.read(1024)
    suffix = path.suffix.lower()
    if head.startswith(b"%PDF-"):
        actual, permitted = "pdf", {".pdf"}
    elif head.startswith(b"\x89PNG\r\n\x1a\n"):
        actual, permitted = "png", {".png"}
    elif head.startswith(b"\xff\xd8\xff"):
        actual, permitted = "jpeg", {".jpg", ".jpeg"}
    elif head.startswith(b"PK"):
        try:
            with zipfile.ZipFile(path) as archive:
                if "word/document.xml" not in archive.namelist():
                    raise AnalysisError("UNSUPPORTED_FORMAT", "ZIP is not a DOCX")
                if sum(i.file_size for i in archive.infolist()) > 256 * 1024 * 1024:
                    raise AnalysisError("INPUT_TOO_LARGE", "Expanded document exceeds 256 MiB")
        except zipfile.BadZipFile as exc:
            raise AnalysisError("DOCUMENT_INVALID", "Invalid DOCX container") from exc
        actual, permitted = "docx", {".docx"}
    elif suffix in {".txt", ".md"}:
        try:
            text = path.read_text("utf-8-sig")
            if "\x00" in text:
                raise ValueError("binary")
        except (UnicodeError, ValueError) as exc:
            raise AnalysisError("ENCODING_UNSUPPORTED", "Text must be UTF-8") from exc
        return suffix[1:]
    else:
        raise AnalysisError("UNSUPPORTED_FORMAT", "No supported adapter for this file")
    if suffix not in permitted:
        raise AnalysisError("FORMAT_MISMATCH", f"Content is {actual}, extension is {suffix}")
    return actual


def _docx_items(path: Path):
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    doc = Document(path)
    items = []

    def walk(container, prefix):
        for i, item in enumerate(container.iter_inner_content(), 1):
            key = f"{prefix}/{i}"
            if isinstance(item, Paragraph):
                if item.text.strip():
                    items.append((key, "text", item.text, []))
                for image_index, element in enumerate(item._p.iter(), 1):
                    if element.tag.endswith("}blip"):
                        relation = element.get(
                            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed")
                        if relation:
                            items.append((f"{key}/image/{image_index}", "image",
                                          doc.part.related_parts[relation].blob, []))
            elif isinstance(item, Table):
                seen = set()
                for ri, row in enumerate(item.rows, 1):
                    for ci, cell in enumerate(row.cells, 1):
                        if cell._tc in seen:
                            continue
                        seen.add(cell._tc)
                        walk(cell, f"{key}/table/row/{ri}/cell/{ci}")
    walk(doc, "body")
    # Footnotes, headers and floating drawings are reported, never silently omitted.
    with zipfile.ZipFile(path) as archive:
        warnings = ["DOCX auxiliary story not imported: " + n for n in archive.namelist()
                    if n.startswith(("word/header", "word/footer", "word/footnotes", "word/endnotes"))
                    and n.endswith(".xml")]
    return items, warnings


def inspect_document(path: Path) -> tuple[str, int]:
    fmt = detect(path)
    try:
        if fmt == "pdf":
            import pypdfium2 as pdfium
            with pdfium.PdfDocument(path) as doc:
                count = len(doc)
        elif fmt == "docx":
            count = len(_docx_items(path)[0])
        elif fmt in {"txt", "md"}:
            count = len(path.read_text("utf-8-sig").splitlines())
        else:
            from PIL import Image
            with Image.open(path) as image:
                image.verify()
            count = 1
        return fmt, count
    except AnalysisError:
        raise
    except Exception as exc:
        raise AnalysisError("DOCUMENT_INVALID", "Unable to inspect document") from exc


def _ocr(image) -> tuple[list, list[str]]:
    from rapidocr import RapidOCR
    import numpy as np
    engine = RapidOCR(params={"Global.log_level": "error"})
    result = engine(np.asarray(image.convert("RGB"))[:, :, ::-1])
    boxes, texts, scores = result.boxes, result.txts, result.scores
    if texts is None:
        return [], ["NO_TEXT_DETECTED"]
    rows = []
    for box, text, score in zip(boxes, texts, scores):
        xs, ys = box[:, 0], box[:, 1]
        rows.append((str(text), [float(min(xs)), float(min(ys)),
                                float(max(xs)), float(max(ys))], float(score)))
    warnings = ["LOW_OCR_CONFIDENCE"] if any(row[2] < .8 for row in rows) else []
    return rows, warnings


def _extract(path: Path, index: int, force_ocr: bool) -> DocumentUnit:
    fmt, count = inspect_document(path)
    if not 1 <= index <= count:
        raise AnalysisError("UNIT_RANGE_INVALID", "Unit is outside the document")
    blocks = []
    warnings = []
    if fmt in {"txt", "md"}:
        text = path.read_text("utf-8-sig").splitlines()[index - 1]
        if text.strip():
            blocks.append(DocumentBlock(text=text, position=DocumentPosition(
                unit=index, structure_path=f"line/{index}")))
        return DocumentUnit(index=index, method="native-text", blocks=blocks)
    if fmt == "docx":
        from PIL import Image
        items, warnings = _docx_items(path)
        structure, kind, payload, _ = items[index - 1]
        if kind == "text":
            return DocumentUnit(index=index, method="docx-structure", warnings=warnings,
                blocks=[DocumentBlock(text=payload, position=DocumentPosition(
                    unit=index, structure_path=structure))])
        image = Image.open(io.BytesIO(payload)).convert("RGB")
        page_size, rotation = list(image.size), 0
    elif fmt == "pdf":
        import pypdfium2 as pdfium
        with pdfium.PdfDocument(path) as doc:
            page = doc[index - 1]
            width, height = page.get_size()
            rotation = page.get_rotation()
            with closing(page.get_textpage()) as textpage:
                text = textpage.get_text_bounded()
                # Replacement glyphs indicate a damaged text layer.
                readable = text.strip() and text.count("\ufffd") <= max(1, len(text) // 20)
                if readable and not force_ocr:
                    textpage.count_rects()
                    for ri in range(textpage.count_rects()):
                        left, bottom, right, top = textpage.get_rect(ri)
                        chunk = textpage.get_text_bounded(left, bottom, right, top)
                        if chunk.strip():
                            blocks.append(DocumentBlock(text=chunk, position=DocumentPosition(
                                unit=index, page=index, region=[left, bottom, right, top],
                                page_size=[width, height], coordinate_unit="pt",
                                origin="bottom-left", rotation=rotation)))
                    if not blocks:
                        blocks.append(DocumentBlock(text=text, position=DocumentPosition(
                            unit=index, page=index, region=[0, 0, width, height],
                            page_size=[width, height], coordinate_unit="pt", origin="bottom-left",
                            rotation=rotation)))
                    warnings.append("NATIVE_LAYOUT_UNREVIEWED: tables/images/order require review")
                    return DocumentUnit(index=index, method="pdf-text", blocks=blocks,
                                        warnings=warnings)
            bitmap = page.render(scale=2)
            image = bitmap.to_pil().copy()
            bitmap.close()
            page_size = [width, height]
        structure = None
    else:
        from PIL import Image, ImageOps
        with Image.open(path) as original:
            image = ImageOps.exif_transpose(original).convert("RGB")
        page_size, rotation, structure = list(image.size), 0, None
    rows, ocr_warnings = _ocr(image)
    warnings.extend(ocr_warnings)
    warnings.append("OCR_LAYOUT_UNREVIEWED: tables/images/order require review")
    for text, region, confidence in rows:
        blocks.append(DocumentBlock(text=text, confidence=confidence,
            position=DocumentPosition(unit=index, page=index if fmt == "pdf" else None,
                structure_path=structure, region=region, page_size=page_size,
                coordinate_unit="rendered-pixel" if fmt == "pdf" else "pixel",
                origin="top-left", render_scale=2 if fmt == "pdf" else 1,
                rotation=rotation)))
    return DocumentUnit(index=index, method="ocr", blocks=blocks, warnings=warnings)


def extract_unit(path: Path, index: int, force_ocr=False, timeout=120) -> DocumentUnit:
    # Isolate native parsers/OCR: timeouts can actually terminate the work.
    try:
        result = subprocess.run([sys.executable, "-m", "medicine_agent.analysis.documents",
            str(path), str(index), "1" if force_ocr else "0"],
            capture_output=True, timeout=timeout, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired as exc:
        raise AnalysisError("EXTRACTION_TIMEOUT", "Document unit extraction timed out") from exc
    try:
        payload = json.loads(result.stdout.split("MEDICINE_RESULT:")[-1])
    except (ValueError, IndexError) as exc:
        raise AnalysisError("EXTRACTION_FAILED", "Extraction worker failed") from exc
    if "error" in payload:
        raise AnalysisError(payload["error"], payload["message"])
    return DocumentUnit.model_validate(payload)


if __name__ == "__main__":
    try:
        unit = _extract(Path(sys.argv[1]), int(sys.argv[2]), sys.argv[3] == "1")
        payload = unit.model_dump(mode="json")
    except Exception as exc:
        payload = {"error": "DEPENDENCY_UNAVAILABLE" if isinstance(exc, ImportError)
                   else getattr(exc, "code", "EXTRACTION_FAILED"),
                   "message": str(exc) if isinstance(exc, AnalysisError) else "Document worker failed"}
    sys.stdout.reconfigure(encoding="utf-8")
    print("MEDICINE_RESULT:" + json.dumps(payload, ensure_ascii=False))
