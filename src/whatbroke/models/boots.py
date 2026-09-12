"""Observed system-journal boot history, not exact machine uptime."""

from dataclasses import dataclass, field
from datetime import datetime

from whatbroke.models.sources import SourceStatus


@dataclass(frozen=True)
class Boot:
    index: int
    boot_id: str
    first_entry: datetime
    last_entry: datetime


@dataclass
class BootCollection:
    status: SourceStatus = SourceStatus.AVAILABLE
    boots: list[Boot] = field(default_factory=list)
    diagnostics: list[str] = field(default_factory=list)
    malformed_records: int = 0
    access_limited: bool = False
    error: str | None = None
