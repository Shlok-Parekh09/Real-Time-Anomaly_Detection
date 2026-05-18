from __future__ import annotations

import hashlib
import json
import sqlite3
from contextlib import closing
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DATABASE_PATH = Path(__file__).resolve().parent / "data" / "document_forensics.sqlite3"
DECISION_TABLES = {
    "accepted": "authorized_docs",
    "rejected": "unauthorized_docs",
}


def _connect() -> sqlite3.Connection:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA journal_mode=WAL")
    return connection


def init_review_database() -> None:
    with closing(_connect()) as connection:
        for table_name in set(DECISION_TABLES.values()):
            connection.execute(
                f"""
                CREATE TABLE IF NOT EXISTS {table_name} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    created_at TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    content_type TEXT NOT NULL,
                    file_sha256 TEXT NOT NULL,
                    file_size INTEGER NOT NULL,
                    risk_score REAL,
                    trust_score REAL,
                    analysis_json TEXT NOT NULL,
                    document_blob BLOB NOT NULL
                )
                """
            )
        connection.commit()


def store_review_document(
    *,
    decision: str,
    file_name: str,
    content_type: str,
    file_bytes: bytes,
    analysis: dict[str, Any],
) -> dict[str, Any]:
    table_name = DECISION_TABLES.get(decision)
    if table_name is None:
        raise ValueError("decision must be accepted or rejected")

    init_review_database()
    created_at = datetime.now(timezone.utc).isoformat()
    file_sha256 = hashlib.sha256(file_bytes).hexdigest()
    analysis_json = json.dumps(analysis, ensure_ascii=True, sort_keys=True)

    with closing(_connect()) as connection:
        cursor = connection.execute(
            f"""
            INSERT INTO {table_name} (
                created_at,
                file_name,
                content_type,
                file_sha256,
                file_size,
                risk_score,
                trust_score,
                analysis_json,
                document_blob
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at,
                file_name,
                content_type,
                file_sha256,
                len(file_bytes),
                analysis.get("risk_score"),
                analysis.get("trust_score"),
                analysis_json,
                sqlite3.Binary(file_bytes),
            ),
        )
        record_id = cursor.lastrowid
        connection.commit()

    return {
        "id": record_id,
        "decision": decision,
        "file_sha256": file_sha256,
        "stored_at": created_at,
    }
