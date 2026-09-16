from __future__ import annotations

import sys
from pathlib import Path

from app.security.secrets import SecretScanner


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED = {".git", ".venv", "venv", "__pycache__", ".pytest_cache"}


def tracked_text_files() -> tuple[Path, ...]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if not path.is_file() or any(part in EXCLUDED for part in path.parts):
            continue
        files.append(path)
    return tuple(files)


def main() -> int:
    findings = SecretScanner().scan_paths(tracked_text_files())
    if findings:
        for finding in findings:
            print(f"SECRET FINDING: {finding.path}:{finding.line} [{finding.rule}]")
        return 1
    print("Secret scan: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
