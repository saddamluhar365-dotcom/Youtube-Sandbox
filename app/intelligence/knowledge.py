from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from .db import Database
from .models import EvidenceType, KnowledgeRecord


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class KnowledgeStore:
    """Persistence API that keeps evidence classes explicit."""

    def __init__(self, db: Database):
        self.db = db
        self.db.initialize()

    def add_fact(
        self,
        topic: str,
        claim: str,
        evidence: str,
        source_name: str | None = None,
        source_url: str | None = None,
        confidence: float = 1.0,
    ) -> int:
        return self._add(
            EvidenceType.OFFICIAL_FACT,
            topic,
            claim,
            evidence,
            source_name,
            source_url,
            confidence,
            "verified",
        )

    def add_observation(
        self,
        topic: str,
        claim: str,
        evidence: str,
        confidence: float = 0.0,
        source_name: str | None = None,
        source_url: str | None = None,
    ) -> int:
        return self._add(
            EvidenceType.OBSERVED_DATA,
            topic,
            claim,
            evidence,
            source_name,
            source_url,
            confidence,
            "observed",
        )

    def add_hypothesis(
        self,
        topic: str,
        claim: str,
        evidence: str,
        confidence: float = 0.0,
    ) -> int:
        return self._add(
            EvidenceType.HYPOTHESIS,
            topic,
            claim,
            evidence,
            None,
            None,
            confidence,
            "unverified",
        )

    def _add(
        self,
        evidence_type: EvidenceType,
        topic: str,
        claim: str,
        evidence: str,
        source_name: str | None,
        source_url: str | None,
        confidence: float,
        status: str,
    ) -> int:
        topic = topic.strip()
        claim = claim.strip()
        evidence = evidence.strip()
        if not topic or not claim or not evidence:
            raise ValueError("topic, claim and evidence are required")
        if not 0.0 <= confidence <= 1.0:
            raise ValueError("confidence must be between 0 and 1")

        with self.db.connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO knowledge_records
                (evidence_type, topic, claim, evidence, source_url, source_name,
                 collected_at, confidence, status, version)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
                """,
                (
                    evidence_type.value,
                    topic,
                    claim,
                    evidence,
                    source_url,
                    source_name,
                    _now(),
                    confidence,
                    status,
                ),
            )
            return int(cursor.lastrowid)

    def get(self, knowledge_id: int) -> KnowledgeRecord | None:
        with self.db.connection() as conn:
            row = conn.execute(
                "SELECT * FROM knowledge_records WHERE knowledge_id = ?",
                (knowledge_id,),
            ).fetchone()
        return self._to_model(row) if row else None

    def list_by_topic(self, topic: str) -> list[KnowledgeRecord]:
        with self.db.connection() as conn:
            rows = conn.execute(
                """
                SELECT * FROM knowledge_records
                WHERE topic = ?
                ORDER BY knowledge_id DESC
                """,
                (topic.strip(),),
            ).fetchall()
        return [self._to_model(row) for row in rows]

    @staticmethod
    def _to_model(row: Any) -> KnowledgeRecord:
        collected_at = None
        if row["collected_at"]:
            try:
                collected_at = datetime.fromisoformat(row["collected_at"])
            except ValueError:
                collected_at = None
        return KnowledgeRecord(
            knowledge_id=int(row["knowledge_id"]),
            evidence_type=EvidenceType(row["evidence_type"]),
            topic=row["topic"],
            claim=row["claim"],
            evidence=row["evidence"],
            source_url=row["source_url"],
            source_name=row["source_name"],
            confidence=float(row["confidence"]),
            status=row["status"],
            version=int(row["version"]),
            collected_at=collected_at,
        )
