"""JSONL file logger for real-time result streaming and backup."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from src.models.result import ScanResult

DEFAULT_JSONL_DIR = Path("data")


class JsonlLogger:
    """Appends scan results to a JSONL file for streaming backup.

    Each line is a self-contained JSON object, making it safe to read
    partial files after crashes or interruptions.
    """

    def __init__(self, scan_id: str, output_dir: Path = DEFAULT_JSONL_DIR) -> None:
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.file_path = self.output_dir / f"scan_{scan_id}.jsonl"

    def log_result(self, result: ScanResult) -> None:
        """Append a single result as a JSON line."""
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(result.model_dump_json() + "\n")

    def log_event(self, event_type: str, data: dict | None = None) -> None:
        """Log a generic event (start, pause, error, etc.)."""
        record = {
            "event": event_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "data": data or {},
        }
        with open(self.file_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")

    def read_results(self) -> list[ScanResult]:
        """Read back all ScanResult entries from the JSONL file."""
        results: list[ScanResult] = []
        if not self.file_path.exists():
            return results
        with open(self.file_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                data = json.loads(line)
                if "event" in data:
                    continue  # skip event records
                results.append(ScanResult.model_validate(data))
        return results
