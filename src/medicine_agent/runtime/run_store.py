from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

from medicine_agent.domain.models import RunRecord


class RunRecordStore(Protocol):
    def save(self, record: RunRecord) -> None: ...

    def get(self, invocation_id: str) -> RunRecord | None: ...

    def list_records(self) -> list[RunRecord]: ...


class InMemoryRunRecordStore:
    def __init__(self) -> None:
        self._records: dict[str, RunRecord] = {}

    def save(self, record: RunRecord) -> None:
        self._records[record.invocation_id] = record

    def get(self, invocation_id: str) -> RunRecord | None:
        return self._records.get(invocation_id)

    def list_records(self) -> list[RunRecord]:
        return list(self._records.values())

    def write_jsonl(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8", newline="\n") as stream:
            for record in self.list_records():
                stream.write(
                    json.dumps(
                        record.model_dump(mode="json"),
                        ensure_ascii=False,
                        sort_keys=True,
                    )
                )
                stream.write("\n")
