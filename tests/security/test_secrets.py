from __future__ import annotations

from pathlib import Path

from app.security.secrets import SecretScanner


def test_scanner_flags_common_secret_assignments(tmp_path: Path) -> None:
    target = tmp_path / "bad.py"
    target.write_text('FAL_KEY_1 = "test-example-secret-123456"\n', encoding="utf-8")
    findings = SecretScanner().scan_paths((target,))
    assert findings
    assert findings[0].path == str(target)


def test_scanner_allows_environment_variable_names_and_examples(tmp_path: Path) -> None:
    target = tmp_path / ".env.example"
    target.write_text("FAL_KEY_1=\nGEMINI_KEY_1=\n", encoding="utf-8")
    assert SecretScanner().scan_paths((target,)) == ()
