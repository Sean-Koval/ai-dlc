"""Durable mutation journal; remote reconciliation bounds cross-machine idempotency."""

import hashlib
import json
import sqlite3
from pathlib import Path


class Journal:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(path, timeout=30)
        self.db.execute("PRAGMA journal_mode=WAL")
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS operations (id TEXT PRIMARY KEY, fingerprint TEXT NOT NULL, status TEXT NOT NULL, result TEXT)"
        )
        self.db.commit()

    def begin(self, operation_id, payload):
        fp = hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        with self.db:
            inserted = (
                self.db.execute(
                    "INSERT OR IGNORE INTO operations VALUES (?, ?, ?, NULL)",
                    (operation_id, fp, "pending"),
                ).rowcount
                == 1
            )
            row = self.db.execute(
                "SELECT fingerprint,status,result FROM operations WHERE id=?", (operation_id,)
            ).fetchone()
            if row[0] != fp:
                raise ValueError("Operation ID payload conflict")
        return {
            "created": inserted,
            "status": row[1],
            "result": json.loads(row[2]) if row[2] else None,
        }

    def uncertain(self, operation_id):
        with self.db:
            self.db.execute(
                "UPDATE operations SET status=? WHERE id=?", ("uncertain", operation_id)
            )

    def succeed(self, operation_id, result):
        with self.db:
            self.db.execute(
                "UPDATE operations SET status=?,result=? WHERE id=?",
                ("succeeded", json.dumps(result), operation_id),
            )
