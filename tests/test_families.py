"""Failure-family grouping must not erase exact evidence or unrelated errors."""
from dataclasses import replace
import unittest

from test_compare import collection
from whatbroke.analysis.compare import compare_collections, signature
from whatbroke.models.sources import SourceStatus
from whatbroke.reporting.compare import render_comparison


def wifi(index, device, kind='iw', code=19):
    prefix = '<error> [1789160536.6679] iwd-manager[0x561a959cff90]: '
    messages = {
        'iw': f'{device}: Failed to find and pin callout binary "/usr/bin/iw": No such file or directory',
        'type': prefix + f'IWD device named {device} is not a Wifi device',
        'index': prefix + f'if_nametoindex failed for Name {device} for Device at /net/connman/iwd/1/9: {code}',
    }
    result = collection(index, [messages[kind]])
    if kind == 'iw':
        result.events = [replace(result.events[0], unit='systemd-udevd.service', identifier='udevd')]
    return result


class FamilyTests(unittest.TestCase):
    def test_known_variants_are_recurring_families(self):
        for kind in ('iw', 'type', 'index'):
            with self.subTest(kind=kind):
                target, old = wifi(0, 'wlan2', kind), wifi(-1, 'wlan0', kind)
                result = compare_collections(target, [old], 1)
                finding = result.findings[0]
                self.assertEqual(finding.classification, 'recurring failure — new variant')
                self.assertEqual(finding.previous_counts, [0])
                self.assertEqual(finding.family_previous_counts, [1])
                self.assertEqual(finding.previous_devices, ['wlan0'])
                self.assertEqual(finding.target_device, 'wlan2')
                self.assertEqual(finding.example.message, target.events[0].message)
                self.assertNotEqual(signature(target.events[0]), signature(old.events[0]))
                self.assertNotIn('NEWLY OBSERVED', render_comparison(result))

    def test_same_variant_stays_recurring(self):
        finding = compare_collections(wifi(0, 'wlan0'), [wifi(-1, 'wlan0')], 1).findings[0]
        self.assertEqual(finding.classification, 'recurring')

    def test_unseen_family_stays_new(self):
        finding = compare_collections(wifi(0, 'wlan2'), [collection(-1)], 1).findings[0]
        self.assertEqual(finding.classification, 'newly observed')

    def test_partial_baseline_does_not_claim_variant_is_new(self):
        old = wifi(-1, 'wlan0')
        old.status = SourceStatus.PARTIAL
        finding = compare_collections(wifi(0, 'wlan2'), [old], 1).findings[0]
        self.assertEqual(finding.classification, 'recurring failure — variant history incomplete')

    def test_path_code_and_source_collisions_do_not_group(self):
        for change in ('path', 'code', 'source', 'suffix'):
            kind = 'index' if change == 'code' else 'iw'
            target, old = wifi(0, 'wlan2', kind), wifi(-1, 'wlan0', kind)
            event = old.events[0]
            if change == 'path':
                event = replace(event, message=event.message.replace('/usr/bin/iw', '/usr/bin/ip'))
            elif change == 'code':
                event = replace(event, message=event.message[:-2] + '20')
            elif change == 'source':
                event = replace(event, unit='other.service')
            else:
                event = replace(event, message=event.message + ' (other failure)')
            old.events = [event]
            finding = compare_collections(target, [old], 1).findings[0]
            self.assertEqual(finding.classification, 'newly observed', change)

    def test_unknown_message_not_globally_normalized(self):
        finding = compare_collections(collection(0, ['wlan2 exploded']),
                                      [collection(-1, ['wlan0 exploded'])], 1).findings[0]
        self.assertIsNone(finding.family_name)
        self.assertEqual(finding.classification, 'newly observed')

    def test_family_counts_accumulate_per_boot(self):
        old = wifi(-1, 'wlan0')
        old.events += wifi(-1, 'wlan1').events * 2
        finding = compare_collections(wifi(0, 'wlan2'), [collection(-2), old], 2).findings[0]
        self.assertEqual(finding.family_previous_counts, [0, 3])
        self.assertEqual(finding.previous_devices, ['wlan0', 'wlan1'])

    def test_iwd_object_path_variant_preserves_original(self):
        old, target = wifi(-1, 'wlan0', 'index'), wifi(0, 'wlan0', 'index')
        target.events = [replace(target.events[0], message=target.events[0].message.replace('/1/9', '/5/12'))]
        finding = compare_collections(target, [old], 1).findings[0]
        self.assertEqual(finding.classification, 'recurring failure — new variant')
        self.assertEqual(finding.previous_devices, ['wlan0'])
        self.assertIn('/5/12', finding.example.message)


if __name__ == '__main__':
    unittest.main()
