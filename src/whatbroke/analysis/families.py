"""Explicit Wi-Fi failure families; never replace device names globally."""
import re

from whatbroke.models.errors import ErrorEvent


def family(event: ErrorEvent, normalized: str) -> tuple[str, str] | None:
    """Return a family message and device label for a recognized whole message.

    The caller retains source identity in the key. Device labels are interface
    names observed in logs, not assertions about physical device identity.
    """
    if event.unit == 'systemd-udevd.service':
        match = re.fullmatch(
            r'(wlan[0-9]+): Failed to find and pin callout binary "/usr/bin/iw": No such file or directory',
            normalized,
        )
        if match:
            return 'Missing /usr/bin/iw for Wi-Fi interface', match[1]
    if event.unit == 'NetworkManager.service' or event.identifier == 'NetworkManager':
        prefix = r'<error> \[<timestamp>\] iwd-manager\[<address>\]: '
        match = re.fullmatch(prefix + r'IWD device named (wlan[0-9]+) is not a Wifi device', normalized)
        if match:
            return 'IWD interface is not a Wifi device', match[1]
        match = re.fullmatch(
            prefix + r'if_nametoindex failed for Name (wlan[0-9]+) for Device at '
            r'/net/connman/iwd/[0-9]+/[0-9]+: ([0-9]+)', normalized,
        )
        if match:
            return f'IWD if_nametoindex failed (error {match[2]})', match[1]
    return None
