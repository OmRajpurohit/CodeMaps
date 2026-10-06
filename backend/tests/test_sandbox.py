from pathlib import Path

import pytest

from backend.app.core.security import SecurityError
from backend.app.ingestion.sandbox import SandboxManager


def test_sandbox_lifecycle(tmp_path: Path):
    manager = SandboxManager(root_dir=tmp_path)
    sandbox = manager.create_sandbox(prefix="test_repo")
    assert sandbox.exists()
    assert sandbox.is_dir()
    assert str(sandbox).startswith(str(tmp_path))

    # Create dummy files
    (sandbox / "code.py").write_text("print('hello')", encoding="utf-8")
    assert (sandbox / "code.py").exists()

    manager.enforce_limits(sandbox)

    # Cleanup
    manager.cleanup_sandbox(sandbox)
    assert not sandbox.exists()


def test_sandbox_enforce_file_limit(tmp_path: Path, monkeypatch):
    manager = SandboxManager(root_dir=tmp_path)
    sandbox = manager.create_sandbox(prefix="limit_test")

    # Set threshold very low for testing
    from backend.app.core.config import settings

    monkeypatch.setattr(settings, "MAX_FILES_PER_REPO", 3)

    for i in range(5):
        (sandbox / f"file_{i}.txt").write_text("data", encoding="utf-8")

    with pytest.raises(SecurityError, match="exceeds limit"):
        manager.enforce_limits(sandbox)

    manager.cleanup_sandbox(sandbox)
