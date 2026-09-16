from __future__ import annotations

from dataclasses import dataclass

from app.intelligence.competitors import CompetitorChannel


@dataclass(frozen=True)
class DiscoveryCandidate:
    channel_id: str | None
    channel_handle: str | None
    title: str
    niche: str | None
    language: str | None
    format_type: str | None
    scale_band: str | None
    discovery_source: str = "unknown"
    channel_url: str | None = None


class CompetitorDiscovery:
    """Selects comparable peer channels from externally discovered candidates."""

    def discover(
        self,
        *,
        niche: str,
        language: str,
        format_type: str,
        scale_band: str,
        candidates: tuple[DiscoveryCandidate, ...],
        limit: int = 10,
    ) -> tuple[CompetitorChannel, ...]:
        if limit <= 0:
            return ()

        target_niche = self._normalize(niche)
        target_language = self._normalize(language)
        target_format = self._normalize(format_type)
        target_scale = self._normalize(scale_band)
        selected: list[CompetitorChannel] = []
        seen: set[str] = set()

        for candidate in candidates:
            if len(selected) >= limit:
                break
            if not candidate.title.strip():
                continue
            if self._normalize(candidate.niche) != target_niche:
                continue
            if self._normalize(candidate.language) != target_language:
                continue
            if self._normalize(candidate.format_type) != target_format:
                continue
            if self._normalize(candidate.scale_band) != target_scale:
                continue

            identity = candidate.channel_id or candidate.channel_handle
            if not identity or identity in seen:
                continue
            seen.add(identity)
            selected.append(
                CompetitorChannel(
                    channel_id=candidate.channel_id,
                    channel_handle=candidate.channel_handle,
                    channel_url=candidate.channel_url,
                    title=candidate.title.strip(),
                    niche=candidate.niche,
                    language=candidate.language,
                    scale_band=candidate.scale_band,
                    discovery_source=candidate.discovery_source,
                )
            )

        return tuple(selected)

    @staticmethod
    def _normalize(value: str | None) -> str:
        return " ".join((value or "").casefold().split())
