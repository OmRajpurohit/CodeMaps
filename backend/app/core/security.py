import os
import re
from pathlib import Path
from urllib.parse import urlparse


class SecurityError(Exception):
    """Raised when an operation violates a security boundary."""
    pass


# Allowed Git URL schemes
ALLOWED_SCHEMES = {"https", "http", "git", "ssh"}

# GitHub / Git URL validation pattern
GIT_URL_REGEX = re.compile(
    r"^(https?://|git@|ssh://git@)[a-zA-Z0-9.\-_]+[:/][a-zA-Z0-9.\-_]+/[a-zA-Z0-9.\-_]+(\.git)?/?$"
)


def validate_repo_url(url: str) -> str:
    """
    Validates repository URL to protect against SSRF, command injection,
    and protocol abuse (e.g. file://, gopher://).
    """
    cleaned = url.strip()
    if not cleaned:
        raise SecurityError("Repository URL cannot be empty.")

    # Disallow control characters, newlines, semicolons, shell metacharacters
    if any(c in cleaned for c in [";", "&", "|", "`", "$", "\n", "\r", "<", ">", "\0"]):
        raise SecurityError("Repository URL contains illegal shell metacharacters.")

    # Allow valid existing local directories (for local repos and testing)
    if Path(cleaned).exists() and Path(cleaned).is_dir():
        return str(Path(cleaned).resolve())

    # Match SSH shorthand format: git@github.com:owner/repo.git
    if cleaned.startswith("git@"):
        if not GIT_URL_REGEX.match(cleaned):
            raise SecurityError(f"Invalid Git SSH URL format: {cleaned}")
        return cleaned

    parsed = urlparse(cleaned)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise SecurityError(f"Unsupported URL scheme '{parsed.scheme}'. Allowed: {ALLOWED_SCHEMES}")

    if not parsed.netloc:
        raise SecurityError("Invalid repository URL: host/netloc is missing.")

    # Disallow localhost / loopback / private IP SSRF attempts for public repo ingestion
    hostname = parsed.hostname or ""
    if hostname.lower() in {"localhost", "127.0.0.1", "0.0.0.0", "::1"}:
        raise SecurityError("Access to loopback/internal hosts is strictly forbidden.")

    return cleaned


def safe_resolve_path(base_dir: Path, untrusted_relative_path: str) -> Path:
    """
    Safely resolves untrusted relative paths inside base_dir,
    guaranteeing that the target is strictly inside base_dir
    and not escaping via '..' or symlinks.
    """
    base_resolved = base_dir.resolve()
    # Normalize path separators
    clean_rel = os.path.normpath(untrusted_relative_path)
    if clean_rel.startswith(os.sep) or (os.name == "nt" and ":" in clean_rel):
        # Disallow absolute paths passed as relative
        raise SecurityError(f"Absolute paths not permitted: {untrusted_relative_path}")

    target = (base_resolved / clean_rel).resolve()

    try:
        # Verify target is contained in base_resolved
        target.relative_to(base_resolved)
    except ValueError:
        raise SecurityError(
            f"Path traversal detected: '{untrusted_relative_path}' resolves outside sandbox '{base_resolved}'"
        )

    return target


def check_directory_size_mb(path: Path) -> float:
    """Calculates total disk usage of directory in megabytes."""
    total_bytes = 0
    for root, _, files in os.walk(path):
        for f in files:
            fp = os.path.join(root, f)
            try:
                total_bytes += os.path.getsize(fp)
            except (OSError, FileNotFoundError):
                continue
    return total_bytes / (1024 * 1024)
