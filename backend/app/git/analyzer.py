import hashlib
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime

import git

from backend.app.core.logging import logger


@dataclass
class ExtractedCommit:
    commit_sha: str
    author_alias: str
    authored_at: datetime
    message: str
    insertions: int
    deletions: int
    files_changed: int


@dataclass
class FileChurnMetric:
    file_path: str
    commit_count: int = 0
    lines_added: int = 0
    lines_deleted: int = 0
    total_churn: int = 0
    author_count: int = 0
    ownership_hhi: float = 1.0  # Herfindahl-Hirschman Index (1.0 = single contributor)
    recent_changes_count: int = 0  # In last 30 commits


@dataclass
class GitAnalysisResult:
    commits: list[ExtractedCommit] = field(default_factory=list)
    file_churns: dict[str, FileChurnMetric] = field(default_factory=dict)
    total_commits: int = 0
    total_authors: int = 0
    top_churn_files: list[str] = field(default_factory=list)


class GitHistoryAnalyzer:
    """
    Analyzes Git repository commit logs to extract churn, contributor concentration,
    and volatility while preserving contributor privacy via salted hashing.
    """

    def __init__(self, salt: str = "codeatlas-salt") -> None:
        self.salt = salt
        self._author_alias_cache: dict[str, str] = {}

    def _anonymize_author(self, name: str, email: str) -> str:
        """
        Derives a deterministic, privacy-preserving pseudonym for an author.
        Does not reveal personal email or full identity.
        """
        identifier = f"{name}:{email}:{self.salt}"
        if identifier not in self._author_alias_cache:
            digest = hashlib.sha256(identifier.encode("utf-8")).hexdigest()[:6]
            alias_index = len(self._author_alias_cache) + 1
            self._author_alias_cache[identifier] = f"Contributor-{alias_index} [{digest}]"
        return self._author_alias_cache[identifier]

    def analyze_repository(
        self,
        repo: git.Repo,
        max_commits: int = 500,
    ) -> GitAnalysisResult:
        logger.info("Extracting Git history (max_commits: %d)...", max_commits)

        commits_list: list[ExtractedCommit] = []
        file_commit_counts: dict[str, int] = defaultdict(int)
        file_insertions: dict[str, int] = defaultdict(int)
        file_deletions: dict[str, int] = defaultdict(int)
        file_author_commits: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
        file_recent_counts: dict[str, int] = defaultdict(int)

        unique_authors: set[str] = set()

        try:
            commits = list(repo.iter_commits(max_count=max_commits))
        except Exception as e:
            logger.warning("Failed to iterate commits: %s", str(e))
            return GitAnalysisResult()

        for idx, commit in enumerate(commits):
            author_alias = self._anonymize_author(
                commit.author.name or "Unknown",
                commit.author.email or "unknown@domain.com",
            )
            unique_authors.add(author_alias)

            authored_at = datetime.fromtimestamp(commit.authored_date, tz=UTC)
            first_line_msg = commit.message.splitlines()[0] if commit.message else ""

            # Extract diff stats
            stats = commit.stats
            insertions = stats.total.get("insertions", 0)
            deletions = stats.total.get("deletions", 0)
            files_changed = stats.total.get("files", 0)

            commits_list.append(
                ExtractedCommit(
                    commit_sha=commit.hexsha,
                    author_alias=author_alias,
                    authored_at=authored_at,
                    message=first_line_msg[:255],
                    insertions=insertions,
                    deletions=deletions,
                    files_changed=files_changed,
                )
            )

            # File-level churn breakdown
            for file_path, fstats in stats.files.items():
                norm_path = file_path.replace("\\", "/")
                file_commit_counts[norm_path] += 1
                file_insertions[norm_path] += fstats.get("insertions", 0)
                file_deletions[norm_path] += fstats.get("deletions", 0)
                file_author_commits[norm_path][author_alias] += 1

                if idx < 30:  # Recent commits window
                    file_recent_counts[norm_path] += 1

        # Calculate FileChurnMetric for each file
        file_churns: dict[str, FileChurnMetric] = {}
        for file_path, count in file_commit_counts.items():
            ins = file_insertions[file_path]
            dels = file_deletions[file_path]
            authors_map = file_author_commits[file_path]

            # Calculate HHI ownership concentration: sum (commits_by_author / total_commits)^2
            hhi = sum((c / count) ** 2 for c in authors_map.values())

            file_churns[file_path] = FileChurnMetric(
                file_path=file_path,
                commit_count=count,
                lines_added=ins,
                lines_deleted=dels,
                total_churn=ins + dels,
                author_count=len(authors_map),
                ownership_hhi=round(hhi, 3),
                recent_changes_count=file_recent_counts[file_path],
            )

        top_churn = sorted(
            file_churns.keys(),
            key=lambda fp: file_churns[fp].total_churn,
            reverse=True,
        )[:10]

        logger.info(
            "Git analysis complete: %d commits, %d files tracked across %d authors.",
            len(commits_list),
            len(file_churns),
            len(unique_authors),
        )

        return GitAnalysisResult(
            commits=commits_list,
            file_churns=file_churns,
            total_commits=len(commits_list),
            total_authors=len(unique_authors),
            top_churn_files=top_churn,
        )


git_history_analyzer = GitHistoryAnalyzer()
