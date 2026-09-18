"""Comparison output with evidence, counts, and explicit coverage limits."""
from whatbroke.analysis.compare import Comparison
from whatbroke.models.sources import SourceStatus
from whatbroke.reporting.packages import _safe
from whatbroke.reporting.history import history_limits


def render_comparison(result: Comparison) -> str:
    complete_count = sum(item.status == SourceStatus.AVAILABLE for item in result.previous)
    lines = [f'Status: {result.status.value}',
             f'Previous boots: requested {result.requested}; selected {len(result.previous)}; '
             f'collected without reported limitations {complete_count}']
    if result.target.history is not None:
        lines.extend(history_limits(result.target.history))
    for label, item in [('Target', result.target), *[(f'Previous {i+1}', item) for i, item in enumerate(result.previous)]]:
        lines.append(f'{label}: {item.boot.boot_id if item.boot else item.selector} · {item.status.value}')
        if item.boot:
            span = item.boot.last_entry - item.boot.first_entry
            lines.append(f'  Observed records: {item.boot.first_entry.isoformat()} – '
                         f'{item.boot.last_entry.isoformat()} (span {span})')
        if item.error:
            lines.append('  ' + _safe(item.error))
        if item.malformed_records:
            lines.append(f'  Skipped error records: {item.malformed_records}')
        lines.extend('  journalctl: ' + _safe(note) for note in item.diagnostics)
    if any(item.access_limited for item in [result.target, *result.previous]):
        lines.append('Journal access is restricted. Rerun with sudo for more details.')
    lines.append('Comparison uses all retained error-or-higher records in each selected boot. '
                 'Spans differ; counts are not rates or equal-duration comparisons.')
    lines.append('Newly observed means absent from the selected readable baseline, not proof of first-ever failure. '
                 'Retained history may have gaps. Exact signatures preserve device names and paths; known Wi-Fi patterns also have family context.')
    if result.empty_records:
        lines.append(f'Empty-message records excluded from target signatures: {result.empty_records}')
    for finding in result.findings:
        event = finding.example
        source = event.unit or event.identifier or event.transport or 'unknown source'
        lines.extend(['', finding.classification.upper(), _safe(f'{source}: {finding.key[-1]}'),
                      f'Target: {finding.count} occurrences',
                      'Previous counts (same order as boots above): ' + (', '.join(
                          str(count) if item.status == SourceStatus.AVAILABLE else f'{count} observed (incomplete)'
                          for count, item in zip(finding.previous_counts, result.previous)) or 'unavailable'),
                      _safe(f'Evidence: {event.timestamp.isoformat()} · {event.message}')])
        if finding.family_name:
            lines.append(_safe(f'Failure family: {finding.family_name}'))
            lines.append('Family previous counts: ' + (', '.join(
                str(count) if item.status == SourceStatus.AVAILABLE else f'{count} observed (incomplete)'
                for count, item in zip(finding.family_previous_counts, result.previous)) or 'unavailable'))
            lines.append(_safe('Previously observed device references: ' +
                               (', '.join(finding.previous_devices) or 'none observed')))
            lines.append(_safe(f'Target variant device reference: {finding.target_device}'))
    if not result.findings:
        lines.append('No non-empty target error signatures observed; this does not establish system health.'
                     if result.target.status == SourceStatus.AVAILABLE else
                     'Target collection is incomplete or unavailable; absence of errors cannot be established.')
    return '\n'.join(lines)
