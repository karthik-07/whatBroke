"""Render visible boot history and its limitations."""

from whatbroke.models.boots import BootCollection
from whatbroke.reporting.packages import _safe
from whatbroke.reporting.history import history_limits


def render_boots(result: BootCollection, limit: int = 20) -> str:
    lines = ["Source: system journal (default namespace)", f"Status: {result.status.value}",
             f"Visible boots: {len(result.boots)}"]
    if result.boots:
        first = min(boot.first_entry for boot in result.boots)
        last = max(boot.last_entry for boot in result.boots)
        lines.append(f"Observed history: {first.isoformat()} – {last.isoformat()}")
    else:
        lines.append("Observed history: unavailable.")
    lines.extend(history_limits(result))
    lines.append(f"Display limit: {limit}. Increasing --limit only displays more available boots; it cannot retrieve older history.")
    if result.error:
        lines.append(_safe(result.error))
    if result.malformed_records:
        lines.append(f"Skipped malformed/duplicate boot records: {result.malformed_records}")
    if result.access_limited:
        lines.append("Journal access is restricted; boots or system records may be hidden. "
                     "Rerun with sudo for more details.")
    lines.extend(f"journalctl: {_safe(line)}" for line in result.diagnostics)
    lines.append("Times describe retained journal entries, not exact boot/shutdown times. "
                 "Coverage may have gaps; unavailable records are not evidence of error-free boots.")
    lines.append("Availability describes readable records, not guaranteed access to every journal file.")
    if result.boots:
        shown = result.boots[-limit:]
        lines.append(f"\nLast {len(shown)} visible boots (UTC):")
        lines.append("  INDEX  BOOT ID                           FIRST ENTRY                 LAST ENTRY")
        for boot in shown:
            lines.append(f"  {boot.index:>5}  {boot.boot_id}  "
                         f"{boot.first_entry.isoformat()}  {boot.last_entry.isoformat()}")
        lines.append("Indices come from journalctl; 0 is its latest listed boot, not proof of the current boot.")
    return "\n".join(lines)
