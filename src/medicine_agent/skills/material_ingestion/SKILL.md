---
name: material-ingestion
description: Read UTF-8 Markdown or TXT test material into source and positioned fragment records.
---

Use this Skill only for supported local test materials. Preserve file identity and positions. Return `UNSUPPORTED_FORMAT` for other formats; do not simulate PDF or DOCX parsing.

Optional structured fields must arrive as an ordered array so repeated keys remain distinct. Preserve the original key, value, occurrence, location, context, mapping candidates, rule version, and review state. Ambiguous or unmapped values remain in the output and produce warnings; never discard or guess them.

