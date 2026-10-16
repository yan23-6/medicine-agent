# Document extraction (material-ingestion family)

Accept one local file and a 1-based unit index; return immutable text blocks,
physical PDF page or DOCX structural position, OCR confidence and quality gaps.
Uses pypdfium2, python-docx, Pillow and local RapidOCR/ONNX CPU. Each extraction
runs in a bounded subprocess; absent dependencies, bad files, mismatched formats,
invalid units and timeouts return explicit errors. No model-based correction.

Version 0.1.0 adds the product multi-format adapter without changing the frozen
T01 text ingestion contract. Tests and operational checks are recorded in T02-P.
