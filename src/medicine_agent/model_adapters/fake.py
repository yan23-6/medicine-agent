from __future__ import annotations

from typing import Any


class FakeModelClient:
    provider = "fake"
    model = "deterministic-v1"

    def generate_json(
        self, *, system: str, user: str, schema: dict[str, Any]
    ) -> dict[str, Any]:
        del system, schema
        statement = user.strip()
        label = statement.splitlines()[0][:80] if statement else "empty"
        return {"label": label, "statement": statement}

