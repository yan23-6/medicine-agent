---
name: tcm-reasoning
description: Build an evidence-linked, unreviewed TCM reasoning candidate graph from a CanonicalCase.
---

This T02-A baseline is deterministic and intentionally narrow. It consumes the shared clinical contract and marks its inferred nodes as TCM-specific; source observations remain general facts. Every inferred node must retain typed evidence links, an inference status, a role, a confidence level, missing evidence, and an unreviewed state. Negated, cancelled, or entered-in-error observations cannot be used as positive support. A single weak observation must not be promoted to a confirmed syndrome. Historical actions are not recommendations. When the independent safety context is absent or not cleared, treatment recommendations remain empty. Do not present this Skill as a complete medical reasoning or safety capability.
