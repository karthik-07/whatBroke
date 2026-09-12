"""Render temporal candidates with source and interval evidence."""
from whatbroke.analysis.correlate import CorrelationReport
from whatbroke.models.sources import SourceStatus
from whatbroke.reporting.packages import _safe


def render_correlation(report: CorrelationReport) -> str:
    packages = report.packages
    lines = ['\nPACKAGE-CHANGE CORRELATION', f'Correlation status: {report.status.value}',
             _safe(f'Package log: {packages.path} · {packages.status.value}')]
    for label, history in [('Observed package records', packages.history),
                           ('Local package records (timezone unknown)', packages.local_history)]:
        if history.earliest:
            lines.append(f'{label}: {history.earliest.isoformat()} – {history.latest.isoformat()}')
    if packages.history.earliest is None:
        lines.append('Timezone-aware package history: unavailable.')
    if packages.error:
        lines.append(_safe(packages.error))
    if packages.malformed_lines:
        lines.append(f'Skipped package-log records: {packages.malformed_lines}')
    if packages.status == SourceStatus.PERMISSION_DENIED:
        lines.append('Package-log access is restricted. Rerun with sudo for more details or supply a readable --log-file.')
    lines.append('Candidates are preceding changes, not proven causes or relevance rankings. '
                 'Only the selected plain-text package log is checked; history may have gaps. '
                 'Install time does not establish when updated code became active.')
    for finding in report.findings:
        lines.extend(['', _safe(f'Failure: {finding.key[-1]}')])
        if finding.start and finding.end:
            lines.append(f'Window (exclusive): {finding.start.isoformat()} < change < {finding.end.isoformat()}')
            lines.append(f'Baseline boot without this observed signature: {finding.baseline_boot_id}')
        lines.extend('Limitation: ' + _safe(note) for note in finding.limitations)
        for event in finding.candidates:
            versions = f'{event.old_version or "(not installed)"} -> {event.new_version or "(removed)"}'
            lines.append(_safe(f'  {event.timestamp.isoformat()} · {event.action} {event.package} ({versions}) '
                               f'· {event.source}:{event.line_number}'))
        if not finding.candidates:
            lines.append('No candidate package changes found in the available, time-aligned records. '
                         'This does not rule out package or other system changes.')
    return '\n'.join(lines)
