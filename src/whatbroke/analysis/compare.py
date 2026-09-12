"""Conservative error signatures and comparisons over visible boot evidence."""
from collections import Counter
from dataclasses import dataclass, field
import re

from whatbroke.analysis.families import family
from whatbroke.collectors.errors import collect_errors
from whatbroke.collectors.journal import collect_boots
from whatbroke.models.errors import ErrorCollection, ErrorEvent
from whatbroke.models.sources import SourceStatus

Signature = tuple[str | None, str | None, str | None, str]


def signature(event: ErrorEvent) -> Signature:
    message = event.message.strip()
    # NetworkManager embeds a realtime timestamp and an object pointer in messages.
    # Restrict these substitutions to its known format; hexadecimal codes, device
    # names, paths, errno values, and other numbers remain meaningful by default.
    if event.unit == 'NetworkManager.service' or event.identifier == 'NetworkManager':
        message = re.sub(r'^(<[^>]+>\s+)\[\d{10}\.\d+\]', r'\1[<timestamp>]', message)
        message = re.sub(r'\b([\w-]+)\[0x[0-9a-fA-F]{8,16}\]', r'\1[<address>]', message)
    return event.unit, event.identifier, event.transport, message


@dataclass
class Finding:
    key: Signature
    example: ErrorEvent
    count: int
    previous_counts: list[int]
    classification: str
    family_name: str | None = None
    family_previous_counts: list[int] = field(default_factory=list)
    previous_devices: list[str] = field(default_factory=list)
    target_device: str | None = None


@dataclass
class Comparison:
    target: ErrorCollection
    previous: list[ErrorCollection]
    requested: int
    findings: list[Finding] = field(default_factory=list)
    status: SourceStatus = SourceStatus.AVAILABLE
    empty_records: int = 0


def compare_collections(target: ErrorCollection, previous: list[ErrorCollection], requested: int) -> Comparison:
    result = Comparison(target, previous, requested)
    complete = (target.status == SourceStatus.AVAILABLE and bool(previous)
                and all(item.status == SourceStatus.AVAILABLE for item in previous))
    if not complete or len(previous) < requested:
        result.status = SourceStatus.PARTIAL
    if target.boot is None:
        result.status = target.status
        return result
    baseline = [Counter(signature(event) for event in item.events if event.message.strip()) for item in previous]
    family_baseline = []
    family_devices = {}
    for item in previous:
        family_counts = Counter()
        for event in item.events:
            exact = signature(event)
            matched = family(event, exact[-1])
            if matched:
                family_key = (*exact[:3], matched[0])
                family_counts[family_key] += 1
                family_devices.setdefault(family_key, set()).add(matched[1])
        family_baseline.append(family_counts)
    counts = Counter(signature(event) for event in target.events if event.message.strip())
    examples = {}
    for event in target.events:
        if event.message.strip():
            examples.setdefault(signature(event), event)
        else:
            result.empty_records += 1
    for key, count in counts.items():
        prior = [counter[key] for counter in baseline]
        classification = 'recurring' if any(prior) else 'newly observed' if complete else 'insufficient history'
        finding = Finding(key, examples[key], count, prior, classification)
        matched = family(examples[key], key[-1])
        if matched:
            finding.family_name, finding.target_device = matched
            family_key = (*key[:3], finding.family_name)
            finding.family_previous_counts = [counter[family_key] for counter in family_baseline]
            finding.previous_devices = sorted(family_devices.get(family_key, set()))
            if not any(prior) and any(finding.family_previous_counts):
                finding.classification = ('recurring failure — new variant' if complete else
                                          'recurring failure — variant history incomplete')
        result.findings.append(finding)
    order = {'newly observed': 0, 'insufficient history': 1,
             'recurring failure — new variant': 2,
             'recurring failure — variant history incomplete': 2, 'recurring': 3}
    result.findings.sort(key=lambda item: (order[item.classification], -item.count, item.key[-1]))
    return result


def collect_comparison(selector: str = 'current', previous: int = 5) -> Comparison:
    if previous < 1:
        raise ValueError('previous must be at least 1')
    history = collect_boots()
    target = collect_errors(selector, history=history)
    if target.boot is None:
        return compare_collections(target, [], previous)
    # Select by journal order, not wall clock (which can jump between boots).
    candidates = [boot for boot in history.boots if boot.index < target.boot.index][-previous:]
    baseline = [collect_errors(boot.boot_id, history=history) for boot in candidates]
    return compare_collections(target, baseline, previous)
