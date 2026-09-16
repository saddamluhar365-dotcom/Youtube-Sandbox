from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class SecretFinding:
    path: str
    line: int
    rule: str


class SecretScanner:
    """Conservative scanner for accidental credential literals in source files."""

    _ASSIGNMENT = re.compile(
        r"\b(?:FAL_KEY|GEMINI_KEY|GEMINI_API_KEY|TAVILY_KEY|HF_TOKEN)(?:_[1-7])?\s*=\s*['\"]([^'\"]{8,})['\"]"
    )
    _AUTH_HEADER = re.compile(r"Authorization\s*[:=].{0,80}\b(?:Bearer|Key)\s+[A-Za-z0-9._-]{16,}", re.I)
    _GENERIC = re.compile(r"\b(?:api[_-]?key|access[_-]?token|secret[_-]?key)\s*=\s*['\"][^'\"]{12,}['\"]", re.I)
    _TEXT_EXTENSIONS = {".py", ".toml", ".yaml", ".yml", ".json", ".js", ".ts", ".tsx", ".jsx", ".md", ".txt", ".ini", ".cfg"}

    def scan_paths(self, paths: Iterable[Path]) -> tuple[SecretFinding, ...]:
        findings: list[SecretFinding] = []
        for path in paths:
            if path.name == ".env.example" or path.suffix.lower() not in self._TEXT_EXTENSIONS:
                continue
            try:
                lines = path.read_text(encoding="utf-8").splitlines()
            except (OSError, UnicodeDecodeError):
                continue
            for number, line in enumerate(lines, 1):
                if self._looks_safe_example(line):
                    continue
                rule = None
                if self._ASSIGNMENT.search(line):
                    rule = "provider-secret-assignment"
                elif self._AUTH_HEADER.search(line):
                    rule = "authorization-literal"
                elif self._GENERIC.search(line):
                    rule = "generic-secret-assignment"
                if rule:
                    findings.append(SecretFinding(str(path), number, rule))
        return tuple(findings)

    @staticmethod
    def _looks_safe_example(line: str) -> bool:
        stripped = line.strip()
        return (
            stripped.startswith("#")
            or "os.getenv(" in stripped
            or "os.environ" in stripped
            or stripped.endswith("=\"\"")
            or stripped.endswith("=''")
            or "YOUR_" in stripped
        )
