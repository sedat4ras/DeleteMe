"""SQLite-backed state manager for scan persistence and resume capability."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import aiosqlite

from src.models.result import ConfidenceLevel, ResultStatus, ScanResult, ScanState

DEFAULT_DB_PATH = Path("data/trace_state.db")


class StateManager:
    """Async SQLite state manager that persists scan progress and results."""

    def __init__(self, db_path: Path = DEFAULT_DB_PATH) -> None:
        self.db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        """Open the database connection and ensure tables exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._db = await aiosqlite.connect(str(self.db_path))
        self._db.row_factory = aiosqlite.Row
        await self._create_tables()

    async def close(self) -> None:
        """Close the database connection."""
        if self._db:
            await self._db.close()
            self._db = None

    async def _create_tables(self) -> None:
        assert self._db is not None
        await self._db.executescript(
            """
            CREATE TABLE IF NOT EXISTS scan_sessions (
                scan_id         TEXT PRIMARY KEY,
                started_at      TEXT NOT NULL,
                completed_queries TEXT NOT NULL DEFAULT '[]',
                pending_queries   TEXT NOT NULL DEFAULT '[]',
                total_results   INTEGER NOT NULL DEFAULT 0,
                is_complete     INTEGER NOT NULL DEFAULT 0,
                last_error      TEXT NOT NULL DEFAULT ''
            );

            CREATE TABLE IF NOT EXISTS scan_results (
                id              TEXT PRIMARY KEY,
                scan_id         TEXT NOT NULL,
                module          TEXT NOT NULL,
                query           TEXT NOT NULL,
                platform        TEXT NOT NULL DEFAULT '',
                url             TEXT NOT NULL DEFAULT '',
                title           TEXT NOT NULL DEFAULT '',
                snippet         TEXT NOT NULL DEFAULT '',
                status          TEXT NOT NULL DEFAULT 'pending',
                confidence      TEXT NOT NULL DEFAULT 'unverified',
                raw_data        TEXT NOT NULL DEFAULT '{}',
                matched_fields  TEXT NOT NULL DEFAULT '[]',
                timestamp       TEXT NOT NULL,
                FOREIGN KEY (scan_id) REFERENCES scan_sessions(scan_id)
            );

            CREATE INDEX IF NOT EXISTS idx_results_scan_id ON scan_results(scan_id);
            CREATE INDEX IF NOT EXISTS idx_results_module  ON scan_results(module);
            CREATE INDEX IF NOT EXISTS idx_results_status  ON scan_results(status);
            """
        )
        await self._db.commit()

    # ── Scan session operations ──────────────────────────────────────

    async def create_session(self, state: ScanState) -> None:
        """Insert a new scan session."""
        assert self._db is not None
        await self._db.execute(
            """
            INSERT INTO scan_sessions
                (scan_id, started_at, completed_queries, pending_queries, total_results, is_complete, last_error)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                state.scan_id,
                state.started_at.isoformat(),
                json.dumps(state.completed_queries),
                json.dumps(state.pending_queries),
                state.total_results,
                int(state.is_complete),
                state.last_error,
            ),
        )
        await self._db.commit()

    async def update_session(self, state: ScanState) -> None:
        """Update an existing scan session."""
        assert self._db is not None
        await self._db.execute(
            """
            UPDATE scan_sessions SET
                completed_queries = ?,
                pending_queries   = ?,
                total_results     = ?,
                is_complete       = ?,
                last_error        = ?
            WHERE scan_id = ?
            """,
            (
                json.dumps(state.completed_queries),
                json.dumps(state.pending_queries),
                state.total_results,
                int(state.is_complete),
                state.last_error,
                state.scan_id,
            ),
        )
        await self._db.commit()

    async def get_session(self, scan_id: str) -> ScanState | None:
        """Load a scan session by ID."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT * FROM scan_sessions WHERE scan_id = ?", (scan_id,)
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return ScanState(
            scan_id=row["scan_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_queries=json.loads(row["completed_queries"]),
            pending_queries=json.loads(row["pending_queries"]),
            total_results=row["total_results"],
            is_complete=bool(row["is_complete"]),
            last_error=row["last_error"],
        )

    async def get_latest_incomplete_session(self) -> ScanState | None:
        """Return the most recent incomplete scan session for resume."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT * FROM scan_sessions WHERE is_complete = 0 ORDER BY started_at DESC LIMIT 1"
        )
        row = await cursor.fetchone()
        if row is None:
            return None
        return ScanState(
            scan_id=row["scan_id"],
            started_at=datetime.fromisoformat(row["started_at"]),
            completed_queries=json.loads(row["completed_queries"]),
            pending_queries=json.loads(row["pending_queries"]),
            total_results=row["total_results"],
            is_complete=bool(row["is_complete"]),
            last_error=row["last_error"],
        )

    # ── Result operations ────────────────────────────────────────────

    async def save_result(self, scan_id: str, result: ScanResult) -> None:
        """Insert a single scan result."""
        assert self._db is not None
        await self._db.execute(
            """
            INSERT OR REPLACE INTO scan_results
                (id, scan_id, module, query, platform, url, title, snippet,
                 status, confidence, raw_data, matched_fields, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.id,
                scan_id,
                result.module,
                result.query,
                result.platform,
                result.url,
                result.title,
                result.snippet,
                result.status.value,
                result.confidence.value,
                json.dumps(result.raw_data),
                json.dumps(result.matched_fields),
                result.timestamp.isoformat(),
            ),
        )
        await self._db.commit()

    async def get_results(self, scan_id: str, status: ResultStatus | None = None) -> list[ScanResult]:
        """Retrieve results for a scan, optionally filtered by status."""
        assert self._db is not None
        if status:
            cursor = await self._db.execute(
                "SELECT * FROM scan_results WHERE scan_id = ? AND status = ? ORDER BY timestamp",
                (scan_id, status.value),
            )
        else:
            cursor = await self._db.execute(
                "SELECT * FROM scan_results WHERE scan_id = ? ORDER BY timestamp",
                (scan_id,),
            )
        rows = await cursor.fetchall()
        return [self._row_to_result(row) for row in rows]

    async def count_results(self, scan_id: str) -> int:
        """Count total results for a scan session."""
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT COUNT(*) as cnt FROM scan_results WHERE scan_id = ?", (scan_id,)
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0

    @staticmethod
    def _row_to_result(row: aiosqlite.Row) -> ScanResult:
        return ScanResult(
            id=row["id"],
            module=row["module"],
            query=row["query"],
            platform=row["platform"],
            url=row["url"],
            title=row["title"],
            snippet=row["snippet"],
            status=ResultStatus(row["status"]),
            confidence=ConfidenceLevel(row["confidence"]),
            raw_data=json.loads(row["raw_data"]),
            matched_fields=json.loads(row["matched_fields"]),
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )
