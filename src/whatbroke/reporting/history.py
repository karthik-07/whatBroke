"""Describe the limits of a boot-discovery snapshot without guessing their cause."""

from whatbroke.models.boots import BootCollection


def history_limits(history: BootCollection) -> list[str]:
    if not history.boots:
        return ['History limit: no readable boot records were returned by this query.']
    earliest = min(boot.first_entry for boot in history.boots)
    return [
        f'History limit: {len(history.boots)} boots visible; earliest record: {earliest.isoformat()}.',
        'Earlier history is unavailable to this query; this does not establish why it is missing.',
    ]
