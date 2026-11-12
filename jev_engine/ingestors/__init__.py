"""Decoupled ingestion, multi-platform reordering, and edge feature vectorization for JEV-Mirror v2.0."""
from .shard_builder import build_distributed_shards, load_raw_records
from .multi_platform_sync import (
    PlatformAggregator,
    IdentityLinkRegistry,
    TimelineReconciler,
)
from .feature_vectorizer import (
    hash_identity_token,
    extract_window_metric_slices,
    compute_latency_volatility,
)

__all__ = [
    "build_distributed_shards",
    "load_raw_records",
    "PlatformAggregator",
    "IdentityLinkRegistry",
    "TimelineReconciler",
    "hash_identity_token",
    "extract_window_metric_slices",
    "compute_latency_volatility",
]
