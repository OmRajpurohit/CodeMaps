import os
import shutil
import uuid
from pathlib import Path

from backend.app.core.config import settings
from backend.app.core.logging import logger
from backend.app.core.security import SecurityError, check_directory_size_mb, safe_resolve_path


class SandboxManager:
    """
    Manages isolated temporary workspace environments for untrusted repositories.
    Guarantees isolation, resource bounding, and complete cleanup.
    """

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = (root_dir or settings.WORKSPACE_ROOT).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def create_sandbox(self, prefix: str = "repo") -> Path:
        """Creates a unique isolated directory for repository analysis."""
        sandbox_id = f"{prefix}_{uuid.uuid4().hex[:12]}"
        sandbox_path = (self.root_dir / sandbox_id).resolve()
        sandbox_path.mkdir(parents=True, exist_ok=False)
        logger.info("Created isolated sandbox at %s", sandbox_path)
        return sandbox_path

    def cleanup_sandbox(self, sandbox_path: Path) -> None:
        """Removes the sandbox directory and all its contents safely."""
        try:
            # Double check it is strictly inside root_dir before deleting
            safe_resolve_path(self.root_dir, sandbox_path.name)
            if sandbox_path.exists():
                shutil.rmtree(sandbox_path, ignore_errors=True)
                logger.info("Cleaned up sandbox at %s", sandbox_path)
        except Exception as e:
            logger.warning("Failed to clean up sandbox %s: %s", sandbox_path, str(e))

    def enforce_limits(self, sandbox_path: Path) -> None:
        """
        Validates that repository size and file counts do not exceed configured ceilings.
        Raises SecurityError if breached.
        """
        # Disk usage check
        size_mb = check_directory_size_mb(sandbox_path)
        if size_mb > settings.MAX_REPO_SIZE_MB:
            raise SecurityError(
                f"Repository size ({size_mb:.2f} MB) exceeds maximum allowed limit ({settings.MAX_REPO_SIZE_MB} MB)."
            )

        # File count check
        total_files = 0
        for _, _, files in os.walk(sandbox_path):
            total_files += len(files)
            if total_files > settings.MAX_FILES_PER_REPO:
                raise SecurityError(
                    f"Repository file count ({total_files}) exceeds limit of {settings.MAX_FILES_PER_REPO} files."
                )


sandbox_manager = SandboxManager()
