---
name: case-distillation
description: Convert an ordered, source-grounded raw medical case into a candidate CanonicalCase.
---

Preserve every raw field, its original JSON type, readable projection, context, time and evidence references. Keep transcription or OCR correction candidates separate from the original value. A normalized value may be text, coding, quantity, range, ratio, boolean, integer, date-time, period, reference or an explicit missing value. Store historical diagnoses and historical actions separately from observations; neither is a current recommendation. Unmapped fields remain in the output and produce a warning. Every output remains unreviewed until a human reviewer confirms it.
