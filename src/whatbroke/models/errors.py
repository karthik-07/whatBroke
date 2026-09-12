"""Structured journal error evidence for one boot."""
from dataclasses import dataclass, field
from datetime import datetime

from whatbroke.models.boots import Boot
from whatbroke.models.sources import SourceStatus


@dataclass(frozen=True)
class ErrorEvent:
    timestamp: datetime
    boot_id: str
    priority: int
    message: str
    unit: str | None
    identifier: str | None
    transport: str | None
    cursor: str | None
    raw: dict


@dataclass
class ErrorCollection:
    selector: str
    status: SourceStatus = SourceStatus.AVAILABLE
    boot: Boot | None = None
    events: list[ErrorEvent] = field(default_factory=list)
    malformed_records: int = 0
    diagnostics: list[str] = field(default_factory=list)
    access_limited: bool = False
    error: str | None = None
