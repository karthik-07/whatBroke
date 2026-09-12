"""Temporal package candidates for newly observed failures; no causal ranking."""
from dataclasses import dataclass, field
from datetime import datetime

from whatbroke.analysis.compare import Comparison, Signature, signature
from whatbroke.models.packages import PackageCollection, PackageEvent
from whatbroke.models.sources import SourceStatus


@dataclass
class Correlation:
    key: Signature
    start: datetime | None = None
    end: datetime | None = None
    baseline_boot_id: str | None = None
    candidates: list[PackageEvent] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)


@dataclass
class CorrelationReport:
    packages: PackageCollection
    findings: list[Correlation] = field(default_factory=list)
    status: SourceStatus = SourceStatus.AVAILABLE


def correlate(comparison: Comparison, packages: PackageCollection) -> CorrelationReport:
    report = CorrelationReport(packages)
    for finding in comparison.findings:
        if finding.classification != 'newly observed':
            continue
        item = Correlation(finding.key)
        report.findings.append(item)
        baseline = [boot for boot, count in zip(comparison.previous, finding.previous_counts)
                    if boot.boot is not None and boot.status == SourceStatus.AVAILABLE and count == 0]
        events = [event for event in comparison.target.events if signature(event) == finding.key]
        if not baseline or not events or comparison.target.status != SourceStatus.AVAILABLE:
            item.limitations.append('No usable absence baseline or target evidence; no time window inferred.')
            report.status = SourceStatus.PARTIAL
            continue
        prior = max(baseline, key=lambda boot: boot.boot.index)
        item.start = prior.boot.last_entry
        item.end = min(event.timestamp for event in events)
        item.baseline_boot_id = prior.boot.boot_id
        if item.start >= item.end:
            item.limitations.append('Baseline time is not before the failure; clock ordering is inconsistent. No candidates selected.')
            report.status = SourceStatus.PARTIAL
            continue
        if packages.status != SourceStatus.AVAILABLE:
            item.limitations.append(f'Package source is {packages.status.value}; candidate history may be incomplete.')
        if packages.warnings:
            item.limitations.extend(packages.warnings)
        if packages.history.earliest is None or packages.history.latest is None:
            item.limitations.append('No timezone-aware package-log history is available.')
        else:
            if packages.history.earliest > item.start:
                item.limitations.append('Package-log records start after the beginning of this window.')
            if packages.history.latest < item.end:
                item.limitations.append('The last package-log record precedes the failure; later coverage is unverified (the log may simply have been idle).')
        if any(event.timestamp.tzinfo is None for event in packages.events):
            item.limitations.append('Package events without a timezone were excluded; their timing cannot be aligned reliably.')
        # Strictly after the baseline and before the failure. Equal timestamps do
        # not establish ordering, particularly with second-resolution package logs.
        item.candidates = sorted((event for event in packages.events
                                  if event.timestamp.tzinfo is not None
                                  and item.start < event.timestamp < item.end),
                                 key=lambda event: (event.timestamp, event.line_number))
        if any(event.timestamp.tzinfo is not None and event.timestamp in (item.start, item.end)
               for event in packages.events):
            item.limitations.append('Changes with timestamps equal to a window boundary were excluded because ordering is ambiguous.')
        if item.limitations:
            report.status = SourceStatus.PARTIAL
    return report
