from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .ingest import PublicChannelIngestor
from .models import ChannelSyncResult
from .resolver import ChannelHandleResolver

PayloadCollector = Callable[[str], dict[str, Any]]


class ChannelSyncService:
    """Handle-first orchestration for resolving and incrementally syncing a public channel."""

    def __init__(
        self,
        resolver: ChannelHandleResolver,
        collector: PayloadCollector,
        ingestor: PublicChannelIngestor,
    ):
        self.resolver = resolver
        self.collector = collector
        self.ingestor = ingestor

    def sync(self, handle: str) -> ChannelSyncResult:
        identity = self.resolver.resolve(handle)
        payload = self.collector(identity.channel_id)
        if not isinstance(payload, dict):
            raise TypeError("channel collector must return a dictionary payload")
        return self.ingestor.ingest(identity, payload)
