import os
from dataclasses import dataclass, field
from pathlib import Path

# Ignored directory names during repository indexing
IGNORED_DIRECTORIES: set[str] = {
    ".git",
    ".github",
    ".venv",
    "venv",
    "env",
    "ENV",
    "node_modules",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    "dist",
    "build",
    "out",
    ".next",
    ".nuxt",
    ".idea",
    ".vscode",
    "coverage",
    ".turbo",
    "target",
}

# Ignored file extensions (binaries, lockfiles, images, compiled objects)
IGNORED_EXTENSIONS: set[str] = {
    ".pyc",
    ".pyo",
    ".pyd",
    ".so",
    ".dll",
    ".dylib",
    ".exe",
    ".bin",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".svg",
    ".ico",
    ".pdf",
    ".zip",
    ".tar",
    ".gz",
    ".lock",
    ".min.js",
    ".min.css",
    ".map",
}

# Language mappings by extension
EXTENSION_TO_LANGUAGE: dict[str, str] = {
    ".py": "Python",
    ".ts": "TypeScript",
    ".tsx": "TypeScript",
    ".js": "JavaScript",
    ".jsx": "JavaScript",
    ".mjs": "JavaScript",
    ".cjs": "JavaScript",
    ".go": "Go",
    ".java": "Java",
    ".rs": "Rust",
    ".c": "C",
    ".cpp": "C++",
    ".cc": "C++",
    ".h": "C/C++ Header",
    ".hpp": "C++ Header",
    ".rb": "Ruby",
    ".php": "PHP",
    ".cs": "C#",
    ".swift": "Swift",
    ".kt": "Kotlin",
    ".scala": "Scala",
    ".sql": "SQL",
    ".sh": "Shell",
    ".bash": "Shell",
}


@dataclass
class FileMetric:
    path: str
    relative_path: str
    language: str
    total_lines: int
    blank_lines: int
    comment_lines: int
    loc: int


@dataclass
class ProjectStructure:
    files: list[FileMetric] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)
    primary_language: str | None = None
    total_files: int = 0
    total_loc: int = 0


class LanguageDetector:
    """Discovers project files, detects languages, and computes basic line statistics."""

    @staticmethod
    def count_file_lines(file_path: Path, language: str) -> tuple[int, int, int, int]:
        """
        Fast line counter returning (total_lines, blank_lines, comment_lines, loc).
        """
        try:
            with open(file_path, encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
        except Exception:
            return 0, 0, 0, 0

        total = len(lines)
        blank = 0
        comment = 0

        # Heuristic comment prefixes
        single_line_prefixes = ("#", "//", "--") if language != "Python" else ("#",)

        for line in lines:
            stripped = line.strip()
            if not stripped:
                blank += 1
            elif any(stripped.startswith(prefix) for prefix in single_line_prefixes):
                comment += 1

        loc = max(0, total - blank - comment)
        return total, blank, comment, loc

    def scan_repository(self, repo_dir: Path) -> ProjectStructure:
        """Indexes all eligible source files in repo_dir."""
        repo_root = repo_dir.resolve()
        files_metrics: list[FileMetric] = []
        lang_loc_counts: dict[str, int] = {}

        for root, dirs, files in os.walk(repo_root):
            # Prune ignored directories in-place
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRECTORIES and not d.startswith(".")]

            for filename in files:
                ext = Path(filename).suffix.lower()
                if ext in IGNORED_EXTENSIONS:
                    continue

                full_path = Path(root) / filename
                # Skip files larger than 1MB to avoid parser stalls
                try:
                    if full_path.stat().st_size > 1_048_576:
                        continue
                except OSError:
                    continue

                language = EXTENSION_TO_LANGUAGE.get(ext)
                if not language:
                    continue

                rel_path = str(full_path.relative_to(repo_root)).replace("\\", "/")
                total, blank, comment, loc = self.count_file_lines(full_path, language)

                metric = FileMetric(
                    path=str(full_path),
                    relative_path=rel_path,
                    language=language,
                    total_lines=total,
                    blank_lines=blank,
                    comment_lines=comment,
                    loc=loc,
                )
                files_metrics.append(metric)
                lang_loc_counts[language] = lang_loc_counts.get(language, 0) + loc

        primary_lang = (
            max(lang_loc_counts, key=lang_loc_counts.get) if lang_loc_counts else None
        )
        total_loc = sum(m.loc for m in files_metrics)

        return ProjectStructure(
            files=files_metrics,
            languages=lang_loc_counts,
            primary_language=primary_lang,
            total_files=len(files_metrics),
            total_loc=total_loc,
        )


language_detector = LanguageDetector()
