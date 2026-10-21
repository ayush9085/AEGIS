"""Collector package for AEGIS."""

from aegis.collectors.allowlist import ALLOWLIST_ITEMS, AllowlistItem
from aegis.collectors.engine import collect_device_evidence, get_collection_plan

__all__ = [
    "ALLOWLIST_ITEMS",
    "AllowlistItem",
    "collect_device_evidence",
    "get_collection_plan",
]
