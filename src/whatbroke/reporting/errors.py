"""Render collected error evidence without claiming diagnosis."""
from whatbroke.models.errors import ErrorCollection
from whatbroke.models.sources import SourceStatus
from whatbroke.reporting.packages import _safe


def render_errors(result: ErrorCollection, limit: int = 20) -> str:
    lines = ['Source: system journal (default namespace)', f'Status: {result.status.value}',
             f'Boot selection: {result.selector}']
    if result.boot:
        lines.extend([f'Boot ID: {result.boot.boot_id}',
                      f'Observed boot history: {result.boot.first_entry.isoformat()} – {result.boot.last_entry.isoformat()}'])
    lines.append(f'Error-or-higher records: {len(result.events)}')
    if result.error:
        lines.append(_safe(result.error))
    if result.malformed_records:
        lines.append(f'Skipped malformed/unsupported records: {result.malformed_records}')
    if result.access_limited:
        lines.append('Journal access is restricted. Rerun with sudo for more details.')
    lines.extend(f'journalctl: {_safe(line)}' for line in result.diagnostics)
    if not result.events and result.status == SourceStatus.AVAILABLE:
        lines.append('No matching errors observed in the available records; this does not establish system health.')
    elif not result.events:
        lines.append('Collection is incomplete or unavailable; absence of errors cannot be established.')
    lines.append('Coverage may have gaps. Only priorities 0–3 are included; warnings and user journals are excluded.')
    if result.events:
        shown = result.events[-limit:]
        lines.append(f'\nLast {len(shown)} errors in journal order (UTC):')
        for event in shown:
            source = event.unit or event.identifier or event.transport or 'unknown source'
            lines.append(_safe(f'  {event.timestamp.isoformat()}  [{event.priority}] {source}: {event.message}'))
    return '\n'.join(lines)
