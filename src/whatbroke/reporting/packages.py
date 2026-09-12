"""Human-readable package collection reports."""

from whatbroke.models.packages import PackageCollection, SourceStatus


def _safe(value: object) -> str:
    """Do not allow log content or paths to inject terminal control sequences."""
    return "".join(c if c.isprintable() else repr(c)[1:-1] for c in str(value))


def render_packages(result: PackageCollection, limit: int = 20) -> str:
    lines = [f"Pacman log: {_safe(result.path)}", f"Status: {result.status.value}"]
    for label, history in (("Observed history", result.history),
                           ("Observed local history (timezone unknown)", result.local_history)):
        if history.earliest is not None:
            lines.append(f"{label}: {history.earliest.isoformat()} – {history.latest.isoformat()}")
    if result.history.earliest is None and result.local_history.earliest is None:
        lines.append("Observed history: unavailable (no readable, valid timestamps).")
    lines.append(f"Package events: {len(result.events)}")
    lines.append(f"Lines read: {result.total_lines}; unrelated/blank: {result.ignored_lines}; "
                 f"malformed/unrecognized: {result.malformed_lines}")
    if result.malformed_examples:
        lines.append("Skipped line examples: " + ", ".join(map(str, result.malformed_examples)))
    if result.error:
        lines.append(result.error)
    if result.status == SourceStatus.PERMISSION_DENIED:
        lines.append("For more details, rerun this command with sudo using a trusted installation, "
                     "or provide a readable copy with --log-file.")
    lines.extend(f"Note: {_safe(warning)}" for warning in result.warnings)
    lines.append("History bounds do not guarantee continuous coverage. Only this file was checked; "
                 "rotated logs and the system journal were not checked.")
    if result.events:
        shown = result.events[-limit:]
        lines.append(f"\nLast {len(shown)} package events in file order:")
        for event in shown:
            versions = (f"{event.old_version} -> {event.new_version}"
                        if event.old_version and event.new_version
                        else event.new_version or event.old_version)
            lines.append(_safe(f"  {event.timestamp.isoformat()}  {event.action} "
                               f"{event.package} ({versions})"))
    elif result.status == SourceStatus.AVAILABLE:
        lines.append("No package events found in this file; this does not establish system health.")
    return "\n".join(lines)
