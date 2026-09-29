---
name: knowledge-package-build-validate
description: Build and validate an experimental knowledge package after source, evidence, and knowledge objects pass schema checks.
---

Build into a temporary directory, validate checksums and evidence references, then atomically expose the candidate package. Never label a failed or partial build as usable. This is not the final package v0 format.

Preserve raw field observations and non-sensitive upstream RunRecords as JSONL package data. Ambiguous and unmapped fields are quality warnings; broken evidence references are blocking errors.

