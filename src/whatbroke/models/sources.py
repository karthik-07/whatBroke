"""Shared data-source availability statuses."""

from enum import StrEnum


class SourceStatus(StrEnum):
    AVAILABLE = "available"
    PARTIAL = "partial"
    PERMISSION_DENIED = "permission_denied"
    NOT_FOUND = "not_found"
    ERROR = "error"
    UNSUPPORTED = "unsupported"


