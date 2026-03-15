"""ScanResult and related schemas for storing OSINT findings."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from uuid import uuid4

from pydantic import BaseModel, Field


class ResultStatus(str, Enum):
    """Lifecycle status of a single scan result."""

    FOUND = "found"
    NOT_FOUND = "not_found"
    ERROR = "error"
    PENDING = "pending"


class ConfidenceLevel(str, Enum):
    """How confident we are that this result belongs to the target."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    UNVERIFIED = "unverified"


class ScanResult(BaseModel):
    """A single finding from an OSINT module."""

    id: str = Field(default_factory=lambda: uuid4().hex[:12], description="Unique result identifier")
    module: str = Field(..., description="Module that produced this result (e.g. 'sherlock', 'dorking')")
    query: str = Field(..., description="The exact search query or input used")
    platform: str = Field(default="", description="Platform / website name if applicable")
    url: str = Field(default="", description="URL of the finding")
    title: str = Field(default="", description="Page title or result headline")
    snippet: str = Field(default="", description="Short text excerpt or description")
    status: ResultStatus = Field(default=ResultStatus.PENDING, description="Status of this finding")
    confidence: ConfidenceLevel = Field(
        default=ConfidenceLevel.UNVERIFIED,
        description="Confidence that this result matches the target",
    )
    raw_data: dict = Field(default_factory=dict, description="Raw API / scrape response for debugging")
    matched_fields: list[str] = Field(
        default_factory=list,
        description="Which UserProfile fields contributed to this hit",
    )
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When this result was recorded",
    )


class ScanState(BaseModel):
    """Tracks overall progress of a scan session for resume capability."""

    scan_id: str = Field(default_factory=lambda: uuid4().hex[:16], description="Unique scan session ID")
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_queries: list[str] = Field(default_factory=list, description="Queries already executed")
    pending_queries: list[str] = Field(default_factory=list, description="Queries still to run")
    total_results: int = Field(default=0, description="Count of results collected so far")
    is_complete: bool = Field(default=False, description="Whether the scan finished")
    last_error: str = Field(default="", description="Last error message, if any")
