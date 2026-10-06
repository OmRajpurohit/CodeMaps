from pathlib import Path

import pytest

from backend.app.core.security import SecurityError, safe_resolve_path, validate_repo_url


def test_validate_repo_url_valid_https():
    url = "https://github.com/fastapi/fastapi.git"
    assert validate_repo_url(url) == url


def test_validate_repo_url_valid_ssh():
    url = "git@github.com:torvalds/linux.git"
    assert validate_repo_url(url) == url


def test_validate_repo_url_rejects_empty():
    with pytest.raises(SecurityError, match="cannot be empty"):
        validate_repo_url("   ")


def test_validate_repo_url_rejects_command_injection():
    malicious = "https://github.com/org/repo; rm -rf /"
    with pytest.raises(SecurityError, match="shell metacharacters"):
        validate_repo_url(malicious)


def test_validate_repo_url_rejects_file_protocol():
    with pytest.raises(SecurityError, match="Unsupported URL scheme"):
        validate_repo_url("file:///etc/passwd")


def test_validate_repo_url_rejects_localhost_ssrf():
    with pytest.raises(SecurityError, match="loopback"):
        validate_repo_url("http://127.0.0.1:8000/repo.git")


def test_safe_resolve_path_within_sandbox(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    child = safe_resolve_path(sandbox, "subdir/file.py")
    assert str(child).startswith(str(sandbox))


def test_safe_resolve_path_detects_traversal(tmp_path: Path):
    sandbox = tmp_path / "sandbox"
    sandbox.mkdir()
    with pytest.raises(SecurityError, match="Path traversal detected"):
        safe_resolve_path(sandbox, "../../etc/passwd")
