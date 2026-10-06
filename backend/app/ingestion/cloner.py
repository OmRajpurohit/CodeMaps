from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import git
from git.exc import GitCommandError

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.security import validate_repo_url


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
    """Clones and inspects repositories safely."""

    @staticmethod
    def clone(
        repo_url: str,
        target_dir: Path,
        branch: str | None = None,
        depth: int | None = None,
    ) -> git.Repo:
        """
        Clones a repository into target_dir with depth control and timeouts.
        Validates URL and raises SecurityError or RuntimeError on failure.
        """
        # Validate URL if it's a remote URL
        if not (Path(repo_url).exists() and Path(repo_url).is_dir()):
            validate_repo_url(repo_url)

        clone_kwargs: dict = {
            "kill_after_timeout": settings.GIT_CLONE_TIMEOUT_SECONDS,
        }
        if depth:
            clone_kwargs["depth"] = depth
        if branch:
            clone_kwargs["branch"] = branch

        logger.info("Cloning %s into %s (branch: %s, depth: %s)", repo_url, target_dir, branch, depth)

        try:
            repo = git.Repo.clone_from(repo_url, str(target_dir), **clone_kwargs)
            logger.info("Clone completed successfully.")
            return repo
        except GitCommandError as e:
            logger.error("Git clone failed: %s", str(e))
            raise RuntimeError(f"Failed to clone repository: {e.stderr or str(e)}") from e
        except Exception as e:
            logger.error("Unexpected clone failure: %s", str(e))
            raise RuntimeError(f"Cloning error: {str(e)}") from e

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
