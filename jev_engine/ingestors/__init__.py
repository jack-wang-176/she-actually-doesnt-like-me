"""Decoupled ingestion and multi-platform reordering adapters for she-dont-love-me."""
from .shard_builder import build_distributed_shards, load_raw_records
from .multi_platform_sync import (
    PlatformAggregator,
    IdentityLinkRegistry,
    TimelineReconciler,
)

__all__ = [
    "build_distributed_shards",
    "load_raw_records",
    "PlatformAggregator",
    "IdentityLinkRegistry",
    "TimelineReconciler",
]
