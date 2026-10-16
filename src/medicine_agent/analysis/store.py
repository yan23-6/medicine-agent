from __future__ import annotations

import contextlib
import hashlib
import json
import os
import re
import sqlite3
import tempfile
from pathlib import Path

from medicine_agent.analysis.models import AnalysisError
from medicine_agent.runtime.files import replace_path


def encoded(value) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value) -> str:
    return hashlib.sha256(encoded(value).encode("utf-8")).hexdigest()


def atomic_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'.',suffix='.tmp',dir=path.parent)
    temp=Path(name)
    try:
        with os.fdopen(fd,'w',encoding='utf-8',newline='\n') as stream:
            stream.write(encoded(value));stream.flush();os.fsync(stream.fileno())
        replace_path(temp,path)
    finally:
        temp.unlink(missing_ok=True)


@contextlib.contextmanager
def process_lock(path: Path):
    """OS-owned lock: released on process death, no stale-PID lock deletion."""
    path.parent.mkdir(parents=True, exist_ok=True)
    # An initializing writer can race with another process locking byte zero on
    # Windows. Unbuffered I/O avoids a failed flush being retried by close(), and
    # initialization contention follows the same retryable contract as locking.
    with path.open("a+b", buffering=0) as stream:
        try:
            stream.seek(0)
            if os.fstat(stream.fileno()).st_size == 0:
                stream.write(b"0")
            stream.seek(0)
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise AnalysisError("TASK_BUSY", "Another process owns this task or package family") from exc
        try:
            yield
        finally:
            stream.seek(0)
            if os.name == "nt":
                msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(stream, fcntl.LOCK_UN)


class JobStore:
    def __init__(self, root: Path):
        self.root = root.resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / "jobs.sqlite3"
        with self.connect() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, parent TEXT, status TEXT NOT NULL,
                    request TEXT NOT NULL, result TEXT, errors TEXT NOT NULL DEFAULT '[]',
                    pause INTEGER NOT NULL DEFAULT 0);
                CREATE TABLE IF NOT EXISTS units (
                    task TEXT NOT NULL, ordinal INTEGER NOT NULL,
                    extraction TEXT, extraction_hash TEXT,
                    analysis TEXT, analysis_hash TEXT,
                    PRIMARY KEY(task, ordinal));
                CREATE TABLE IF NOT EXISTS calls (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    task TEXT NOT NULL, record TEXT NOT NULL);
            """)

    @contextlib.contextmanager
    def connect(self):
        db = sqlite3.connect(self.path, timeout=10)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA synchronous=FULL")
        try:
            with db:
                yield db
        finally:
            db.close()

    def task_dir(self, task_id):
        if not re.fullmatch(r"(?:job|analysis)_[a-f0-9]{32}", task_id):
            raise AnalysisError("TASK_ID_INVALID", "Invalid task identity")
        path = self.root / task_id
        if not path.resolve().is_relative_to(self.root):
            raise AnalysisError("PATH_INVALID", "Task directory escapes workspace")
        return path

    def get(self, task_id):
        self.task_dir(task_id)
        with self.connect() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise AnalysisError("TASK_NOT_FOUND", "Task not found")
        return dict(row)

    def children(self, parent):
        self.get(parent)
        with self.connect() as db:
            return [r[0] for r in db.execute(
                "SELECT id FROM tasks WHERE parent=? ORDER BY rowid", (parent,))]

    def update(self, task_id, **values):
        if not set(values) <= {"status", "result", "errors", "pause", "request"}:
            raise ValueError("Unknown task column")
        with self.connect() as db:
            db.execute("UPDATE tasks SET " + ",".join(k + "=?" for k in values)
                       + " WHERE id=?", (*values.values(), task_id))

    def rows(self, task):
        with self.connect() as db:
            return [dict(r) for r in db.execute(
                "SELECT * FROM units WHERE task=? ORDER BY ordinal", (task,))]

    def commit_stage(self, task, ordinal, stage, payload):
        if stage not in {"extraction", "analysis"}:
            raise ValueError(stage)
        with self.connect() as db:
            db.execute(f"UPDATE units SET {stage}=?,{stage}_hash=? WHERE task=? AND ordinal=?",
                       (encoded(payload), digest(payload), task, ordinal))

    def recover(self, task):
        """Corruption invalidates dependent stages, including following context."""
        invalid_context = False
        with self.connect() as db:
            for row in self.rows(task):
                for stage in ("extraction", "analysis"):
                    payload = row[stage]
                    valid = True
                    if payload:
                        try:
                            valid = digest(json.loads(payload)) == row[stage + "_hash"]
                        except (ValueError, TypeError):
                            valid = False
                    if stage == "extraction" and not valid:
                        db.execute("UPDATE units SET extraction=NULL,extraction_hash=NULL WHERE task=? AND ordinal=?",
                                   (task, row["ordinal"]))
                    if (payload and not valid) or (stage == "analysis" and invalid_context):
                        db.execute("UPDATE units SET analysis=NULL,analysis_hash=NULL WHERE task=? AND ordinal=?",
                                   (task, row["ordinal"]))
                        invalid_context = True

    def record(self, task, value):
        with self.connect() as db:
            db.execute("INSERT INTO calls(task,record) VALUES (?,?)", (task, encoded(value)))

    def calls(self, task):
        with self.connect() as db:
            return [json.loads(r[0]) for r in db.execute(
                "SELECT record FROM calls WHERE task=? ORDER BY sequence", (task,))]
