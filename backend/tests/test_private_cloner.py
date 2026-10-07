import os
import pytest
from unittest.mock import patch, MagicMock
from git.exc import GitCommandError
from backend.app.core.security import mask_repo_url, validate_repo_url, SecurityError
from backend.app.ingestion.cloner import GitCloner
from backend.app.core.config import settings


def test_mask_repo_url():
    # Token in URL
    url1 = "https://ghp_secretToken12345@github.com/owner/repo.git"
    assert mask_repo_url(url1) == "https://***@github.com/owner/repo.git"

    # User:Token in URL
    url2 = "https://myuser:ghp_secretToken12345@github.com/owner/repo.git"
    assert mask_repo_url(url2) == "https://myuser:***@github.com/owner/repo.git"

    # Public URL unchanged
    url3 = "https://github.com/owner/repo.git"
    assert mask_repo_url(url3) == "https://github.com/owner/repo.git"

    # SSH URL unchanged
    url4 = "git@github.com:owner/repo.git"
    assert mask_repo_url(url4) == "git@github.com:owner/repo.git"


def test_prepare_clone_url_with_token():
    with patch.object(settings, "GITHUB_TOKEN", "ghp_mockToken123"):
        prepared = GitCloner._prepare_clone_url("https://github.com/owner/private-repo.git")
        assert "x-access-token:ghp_mockToken123@github.com" in prepared

    with patch.object(settings, "GITHUB_TOKEN", ""):
        with patch.object(settings, "GIT_TOKEN", "tokenXYZ"):
            with patch.object(settings, "GIT_USERNAME", "ci_user"):
                prepared = GitCloner._prepare_clone_url("https://gitlab.com/owner/private-repo.git")
                assert "ci_user:tokenXYZ@gitlab.com" in prepared


def test_private_repo_helpful_error_message(tmp_path):
    mock_error = GitCommandError("clone", 128, stderr="fatal: could not read Username for 'https://github.com': terminal prompts disabled")
    
    with patch("git.Repo.clone_from", side_effect=mock_error):
        with pytest.raises(RuntimeError) as exc_info:
            GitCloner.clone("https://github.com/owner/private-repo.git", tmp_path / "repo")
        
        err_msg = str(exc_info.value)
        assert "Authentication failed or repository not found" in err_msg
        assert "GITHUB_TOKEN" in err_msg
