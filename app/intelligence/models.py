from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Any


class EvidenceType(StrEnum):
    OFFICIAL_FACT = "official_fact"
    OBSERVED_DATA = "observed_data"
    EXTERNAL_EVIDENCE = "external_evidence"
    HYPOTHESIS = "hypothesis"


@dataclass(frozen=True)
class KnowledgeRecord:
    knowledge_id: int
    evidence_type: EvidenceType
    topic: str
    claim: str
    evidence: str
    source_url: str | None
    source_name: str | None
    confidence: float
    status: str
    version: int
    collected_at: datetime | None = None


@dataclass(frozen=True)
class ChannelIdentity:
    channel_id: str
    channel_handle: str
    channel_url: str
    title: str | None = None


@dataclass(frozen=True)
class SyncRecord:
    source_id: str
    data_hash: str
    changed: bool
    is_new: bool
    metadata: dict[str, Any]
