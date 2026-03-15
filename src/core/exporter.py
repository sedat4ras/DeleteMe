"""Export scan results to JSON and CSV reports."""

from __future__ import annotations

import csv
import json
from datetime import datetime, timezone
from pathlib import Path

from src.models.result import ScanResult

DEFAULT_OUTPUT_DIR = Path("data")


class Exporter:
    """Export scan results to various formats."""

    def __init__(self, scan_id: str, output_dir: Path = DEFAULT_OUTPUT_DIR) -> None:
        self.scan_id = scan_id
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def to_json(self, results: list[ScanResult]) -> Path:
        """Export results to a JSON file."""
        path = self.output_dir / f"report_{self.scan_id}.json"
        data = {
            "scan_id": self.scan_id,
            "exported_at": datetime.now(timezone.utc).isoformat(),
            "total_results": len(results),
            "found": sum(1 for r in results if r.status.value == "found"),
            "results": [json.loads(r.model_dump_json()) for r in results],
        }
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        return path

    def to_csv(self, results: list[ScanResult]) -> Path:
        """Export results to a CSV file."""
        path = self.output_dir / f"report_{self.scan_id}.csv"
        fieldnames = [
            "id", "module", "query", "platform", "url",
            "title", "snippet", "status", "confidence", "timestamp",
        ]
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for r in results:
                writer.writerow({
                    "id": r.id,
                    "module": r.module,
                    "query": r.query,
                    "platform": r.platform,
                    "url": r.url,
                    "title": r.title,
                    "snippet": r.snippet,
                    "status": r.status.value,
                    "confidence": r.confidence.value,
                    "timestamp": r.timestamp.isoformat(),
                })
        return path
