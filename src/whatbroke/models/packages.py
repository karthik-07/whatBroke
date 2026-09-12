"""Source-independent package events and collection outcomes."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from whatbroke.models.sources import SourceStatus


@dataclass(frozen=True)
class PackageEvent:
    timestamp: datetime
    action: str
    package: str
    old_version: str | None
    new_version: str | None
    source: Path
    line_number: int
    raw: str


@dataclass
class HistoryRange:
    earliest: datetime | None = None
    latest: datetime | None = None

    def include(self, timestamp: datetime) -> None:
        self.earliest = min(self.earliest, timestamp) if self.earliest else timestamp
        self.latest = max(self.latest, timestamp) if self.latest else timestamp


@dataclass
class PackageCollection:
    path: Path
    status: SourceStatus = SourceStatus.AVAILABLE
    events: list[PackageEvent] = field(default_factory=list)
    history: HistoryRange = field(default_factory=HistoryRange)
    local_history: HistoryRange = field(default_factory=HistoryRange)
    total_lines: int = 0
    ignored_lines: int = 0
    malformed_lines: int = 0
    malformed_examples: list[int] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    error: str | None = None
