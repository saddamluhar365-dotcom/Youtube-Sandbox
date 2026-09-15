from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ProviderName(str, Enum):
    TAVILY = "tavily"
    GEMINI = "gemini"
    HUGGING_FACE = "huggingface"
    FAL = "fal.ai"


@dataclass(frozen=True)
class CredentialSlot:
    provider: ProviderName
    slot_id: str
    secret: str

    @property
    def configured(self) -> bool:
        return bool(self.secret)


@dataclass(frozen=True)
class CredentialLease:
    provider: ProviderName
    slot_id: str
    secret: str

    def redacted(self) -> str:
        return f"{self.provider.value}:{self.slot_id}"


@dataclass(frozen=True)
class ProviderProfile:
    name: ProviderName
    capability: str
    max_credentials: int = 7
