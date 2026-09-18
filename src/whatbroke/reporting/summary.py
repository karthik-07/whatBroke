"""Compact comparison report; detailed renderers retain all original evidence."""
from dataclasses import dataclass, field

from whatbroke.analysis.compare import Comparison, Finding
from whatbroke.analysis.correlate import CorrelationReport
from whatbroke.models.sources import SourceStatus
from whatbroke.reporting.compare import render_comparison
from whatbroke.reporting.correlate import render_correlation
from whatbroke.reporting.history import history_limits
from whatbroke.reporting.packages import _safe


@dataclass
class Group:
    title: str
    findings: list[Finding] = field(default_factory=list)

    @property
    def count(self) -> int:
        return sum(finding.count for finding in self.findings)

    @property
    def classification(self) -> str:
        if any(any(f.previous_counts) or any(f.family_previous_counts) for f in self.findings):
            return 'Recurring'
        if all(f.classification == 'newly observed' for f in self.findings):
            return 'Newly observed'
        return 'Insufficient history'


def groups(result: Comparison) -> list[Group]:
    grouped = {}
    for finding in result.findings:
        identity = ('family' if finding.family_name else 'exact',
                    *finding.key[:3], finding.family_name or finding.key[-1])
        if identity not in grouped:
            source = next((part for part in finding.key[:3] if part), 'unknown source')
            grouped[identity] = Group(f'{source}: {identity[-1]}')
        grouped[identity].findings.append(finding)
    order = {'Newly observed': 0, 'Insufficient history': 1, 'Recurring': 2}
    return sorted(grouped.values(), key=lambda group: (order[group.classification], -group.count, group.title))


def overall_status(comparison: Comparison, correlation: CorrelationReport | None) -> SourceStatus:
    if correlation is not None and correlation.status != SourceStatus.AVAILABLE:
        return SourceStatus.PARTIAL if comparison.status == SourceStatus.AVAILABLE else comparison.status
    return comparison.status


def render_report(result: Comparison, correlation: CorrelationReport | None = None,
                  *, verbose: bool = False) -> str:
    status = overall_status(result, correlation)
    lines = [f'Overall status: {status.value}']
    if verbose:
        details = render_comparison(result).splitlines()
        details[0] = f'Comparison status: {result.status.value}'
        lines.extend(details)
        if correlation is not None:
            lines.append(render_correlation(correlation))
        return '\n'.join(lines)

    complete = sum(item.status == SourceStatus.AVAILABLE for item in result.previous)
    lines.append(f'Previous boots: requested {result.requested}; selected {len(result.previous)}; usable {complete}')
    lines.append(_safe(f'Target: {result.target.selector} · {result.target.status.value}'))
    if result.target.history is not None:
        history = result.target.history
        if history.boots:
            first = min(boot.first_entry for boot in history.boots)
            last = max(boot.last_entry for boot in history.boots)
            lines.append(f'Journal history (UTC): {first.isoformat()} – {last.isoformat()} · {len(history.boots)} boots visible')
            lines.append('Earlier history is unavailable to this query; the cause is unknown.')
        else:
            lines.extend(history_limits(history))
    if result.target.boot:
        spans = [item.boot.last_entry - item.boot.first_entry for item in result.previous if item.boot]
        span = result.target.boot.last_entry - result.target.boot.first_entry
        lines.append(f'Observed spans: target {span}' + (f'; previous {min(spans)} to {max(spans)}' if spans else ''))
    notices = []
    for item in [result.target, *result.previous]:
        if item.status != SourceStatus.AVAILABLE:
            notices.append(f'Boot {item.boot.index if item.boot else item.selector}: {item.status.value}')
        if item.error:
            notices.append(item.error)
        if item.malformed_records:
            notices.append(f'Boot {item.selector}: {item.malformed_records} error records skipped.')
        notices.extend(item.diagnostics)
    lines.extend('Notice: ' + _safe(note) for note in dict.fromkeys(notices))
    if any(item.access_limited for item in [result.target, *result.previous]):
        lines.append('Journal access is restricted. Rerun with sudo for more details.')

    grouped = groups(result)
    for label in ('Newly observed', 'Insufficient history', 'Recurring'):
        selected = [group for group in grouped if group.classification == label]
        if not selected:
            continue
        lines.append(f'\n{label} groups: {len(selected)}')
        for group in selected:
            variants = sum('variant' in finding.classification for finding in group.findings)
            uncertain = any(f.classification.endswith('history incomplete') for f in group.findings)
            suffix = f'; {variants} variant(s)' if variants else ''
            if uncertain:
                suffix += ' (variant history incomplete)'
            lines.append(_safe(f'  {group.title} · {group.count} occurrence(s){suffix}'))
    if not grouped:
        lines.append('No non-empty target signatures observed; this does not establish system health.'
                     if result.target.status == SourceStatus.AVAILABLE else
                     'Target collection is incomplete or unavailable; absence of errors cannot be established.')
    if result.empty_records:
        lines.append(f'Empty target messages excluded: {result.empty_records}')

    if correlation is not None:
        lines.extend(['\nPACKAGE-CHANGE CORRELATION', f'Correlation status: {correlation.status.value}',
                      _safe(f'Package log: {correlation.packages.path} · {correlation.packages.status.value}')])
        history = correlation.packages.history
        if history.earliest and history.latest:
            lines.append(f'Observed package records: {history.earliest.isoformat()} – {history.latest.isoformat()}')
        else:
            lines.append('Timezone-aware package history: unavailable.')
        if correlation.packages.error:
            lines.append(_safe(correlation.packages.error))
        if correlation.packages.malformed_lines:
            lines.append(f'Skipped package-log records: {correlation.packages.malformed_lines}')
        if correlation.packages.status == SourceStatus.PERMISSION_DENIED:
            lines.append('Package-log access is restricted. Rerun with sudo or supply a readable --log-file.')
        candidates = {}
        for finding in correlation.findings:
            for event in finding.candidates:
                candidates[(event.source, event.line_number)] = event
        if candidates:
            lines.append(f'{len(candidates)} unique candidate changes across the selected windows:')
            for event in sorted(candidates.values(), key=lambda event: (event.timestamp, str(event.source), event.line_number)):
                lines.append(_safe(f'  {event.timestamp.isoformat()} · {event.action} {event.package} '
                                   f'({event.old_version or "not installed"} -> {event.new_version or "removed"})'))
        else:
            lines.append('No candidate package changes found in the selected windows; this does not rule out other changes.')
        limitations = dict.fromkeys(note for finding in correlation.findings for note in finding.limitations)
        lines.extend('Limitation: ' + _safe(note) for note in limitations)
        lines.append('Candidates are preceding changes, not proven causes. Use --verbose for per-failure windows and source lines.')
    lines.extend(['', 'Newly observed is relative to the selected baseline. History may have gaps.',
                  'Boot spans differ; counts are not rates. Use --verbose for exact variants, per-boot counts, and evidence.'])
    return '\n'.join(lines)
