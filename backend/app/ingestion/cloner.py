from dataclasses import dataclass
from datetime import UTC, datetime
import os
from pathlib import Path
import sys

import git
from git.exc import GitCommandError

from urllib.parse import urlparse, urlunparse

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.security import mask_repo_url, validate_repo_url


@dataclass
class ClonedRepoMetadata:
    commit_sha: str
    branch_name: str
    author_name: str
    author_email: str
    commit_date: datetime
    commit_message: str
    total_commits: int


class GitCloner:
    """Clones and inspects repositories safely, supporting public and private repositories."""

    @staticmethod
    def _prepare_clone_url(repo_url: str) -> str:
        """
        Injects authentication credentials for private repositories if available in settings/env.
        """
        parsed = urlparse(repo_url)
        # If remote HTTPS repository without embedded credentials, inject token if available
        if parsed.scheme in {"https", "http"} and "@" not in parsed.netloc:
            token = (
                settings.GITHUB_TOKEN
                or settings.GIT_TOKEN
                or os.environ.get("GITHUB_TOKEN")
                or os.environ.get("GIT_TOKEN")
            )
            username = settings.GIT_USERNAME or os.environ.get("GIT_USERNAME") or ""
            if token:
                if "github.com" in parsed.netloc.lower():
                    auth_netloc = f"x-access-token:{token}@{parsed.netloc}"
                elif username:
                    auth_netloc = f"{username}:{token}@{parsed.netloc}"
                else:
                    auth_netloc = f"oauth2:{token}@{parsed.netloc}"
                return urlunparse(parsed._replace(netloc=auth_netloc))
        return repo_url

    @staticmethod
    def clone(
        repo_url: str,
        target_dir: Path,
        branch: str | None = None,
        depth: int | None = None,
    ) -> git.Repo:
        """
        Clones a repository into target_dir with depth control, timeouts, and private repo support.
        Validates URL and raises SecurityError or RuntimeError on failure.
        """
        # Validate URL if it's a remote URL
        if not (Path(repo_url).exists() and Path(repo_url).is_dir()):
            validate_repo_url(repo_url)

        clone_env = os.environ.copy()
        clone_env["GIT_TERMINAL_PROMPT"] = "0"

        clone_kwargs: dict = {
            "env": clone_env,
        }
        if sys.platform != "win32" and settings.GIT_CLONE_TIMEOUT_SECONDS:
            clone_kwargs["kill_after_timeout"] = settings.GIT_CLONE_TIMEOUT_SECONDS
        if depth:
            clone_kwargs["depth"] = depth
        if branch:
            clone_kwargs["branch"] = branch

        effective_url = GitCloner._prepare_clone_url(repo_url)
        logger.info(
            "Cloning %s into %s (branch: %s, depth: %s)",
            mask_repo_url(repo_url),
            target_dir,
            branch,
            depth,
        )

        try:
            repo = git.Repo.clone_from(effective_url, str(target_dir), **clone_kwargs)
            logger.info("Clone completed successfully.")
            return repo
        except GitCommandError as e:
            raw_err = e.stderr or str(e)
            masked_err = mask_repo_url(raw_err)
            logger.error("Git clone failed: %s", masked_err)

            err_lower = raw_err.lower()
            if any(
                k in err_lower
                for k in [
                    "could not read username",
                    "terminal prompts disabled",
                    "authentication failed",
                    "repository not found",
                    "permission denied (publickey)",
                    "access denied",
                    "remote: repository not found",
                ]
            ):
                raise RuntimeError(
                    f"Authentication failed or repository not found for '{mask_repo_url(repo_url)}'. "
                    f"If this is a private repository, please configure GITHUB_TOKEN in your environment "
                    f"or provide an authenticated repository URL (e.g., https://<token>@github.com/owner/repo "
                    f"or SSH git@github.com:owner/repo.git). Original error: {masked_err}"
                ) from e

            raise RuntimeError(f"Failed to clone repository: {masked_err}") from e
        except Exception as e:
            masked_err = mask_repo_url(str(e))
            logger.error("Unexpected clone failure: %s", masked_err)
            raise RuntimeError(f"Cloning error: {masked_err}") from e

    @staticmethod
    def extract_metadata(repo: git.Repo) -> ClonedRepoMetadata:
        """Extracts HEAD commit metadata from cloned repository."""
        try:
            head_commit = repo.head.commit
            branch_name = (
                repo.active_branch.name
                if not repo.head.is_detached
                else head_commit.hexsha[:8]
            )

            # Total commits count safely
            try:
                commit_count = sum(1 for _ in repo.iter_commits())
            except Exception:
                commit_count = 1

            authored_date = datetime.fromtimestamp(
                head_commit.authored_date, tz=UTC
            )

            return ClonedRepoMetadata(
                commit_sha=head_commit.hexsha,
                branch_name=branch_name,
                author_name=head_commit.author.name,
                author_email=head_commit.author.email,
                commit_date=authored_date,
                commit_message=head_commit.message.strip(),
                total_commits=commit_count,
            )
        except Exception as e:
            logger.warning("Failed to extract full commit metadata: %s", str(e))
            return ClonedRepoMetadata(
                commit_sha="0" * 40,
                branch_name="main",
                author_name="Unknown",
                author_email="unknown@example.com",
                commit_date=datetime.now(UTC),
                commit_message="Initial import",
                total_commits=1,
            )


git_cloner = GitCloner()
