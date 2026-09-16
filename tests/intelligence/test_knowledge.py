from pathlib import Path

from app.intelligence.db import Database
from app.intelligence.knowledge import KnowledgeStore
from app.intelligence.models import EvidenceType


def test_knowledge_records_preserve_evidence_type(tmp_path: Path) -> None:
    db = Database(tmp_path / "memory.db")
    db.initialize()
    store = KnowledgeStore(db)

    fact_id = store.add_fact(
        topic="recommendations",
        claim="Recommendations are personalized",
        evidence="Documented by YouTube Help",
        source_name="YouTube Help",
        source_url="https://support.google.com/youtube/",
        confidence=0.98,
    )
    hypothesis_id = store.add_hypothesis(
        topic="hooks",
        claim="A faster opening may reduce early swipes",
        evidence="Pending channel experiment",
        confidence=0.4,
    )

    fact = store.get(fact_id)
    hypothesis = store.get(hypothesis_id)

    assert fact is not None
    assert hypothesis is not None
    assert fact.evidence_type is EvidenceType.OFFICIAL_FACT
    assert hypothesis.evidence_type is EvidenceType.HYPOTHESIS
    assert fact.status == "verified"
    assert hypothesis.status == "unverified"


def test_knowledge_topic_filter_returns_only_matching_records(tmp_path: Path) -> None:
    db = Database(tmp_path / "memory.db")
    db.initialize()
    store = KnowledgeStore(db)
    store.add_fact("search", "A", "evidence")
    store.add_observation("shorts", "B", "observation", confidence=0.7)

    records = store.list_by_topic("search")
    assert len(records) == 1
    assert records[0].topic == "search"
