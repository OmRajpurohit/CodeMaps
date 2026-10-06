
from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base, TimestampMixin, UUIDMixin


class Repository(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "repositories"

    url: Mapped[str] = mapped_column(String(512), unique=True, index=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    default_branch: Mapped[str] = mapped_column(String(100), default="main", nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    primary_language: Mapped[str | None] = mapped_column(String(50), nullable=True)
    stars: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    forks: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    analysis_runs: Mapped[list["AnalysisRun"]] = relationship(
        "AnalysisRun", back_populates="repository", cascade="all, delete-orphan"
    )


class AnalysisRun(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "analysis_runs"

    repository_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("repositories.id", ondelete="CASCADE"), index=True, nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    status: Mapped[str] = mapped_column(
        String(50), default="QUEUED", index=True, nullable=False
    )  # QUEUED, CLONING, PARSING, GRAPH_BUILDING, COMPLETED, FAILED
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_stats: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    started_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    repository: Mapped["Repository"] = relationship("Repository", back_populates="analysis_runs")
    files: Mapped[list["FileNode"]] = relationship(
        "FileNode", back_populates="analysis_run", cascade="all, delete-orphan"
    )
    symbols: Mapped[list["Symbol"]] = relationship(
        "Symbol", back_populates="analysis_run", cascade="all, delete-orphan"
    )
    edges: Mapped[list["GraphEdge"]] = relationship(
        "GraphEdge", back_populates="analysis_run", cascade="all, delete-orphan"
    )
    commits: Mapped[list["GitCommit"]] = relationship(
        "GitCommit", back_populates="analysis_run", cascade="all, delete-orphan"
    )
    file_churns: Mapped[list["GitFileChurn"]] = relationship(
        "GitFileChurn", back_populates="analysis_run", cascade="all, delete-orphan"
    )
    hotspots: Mapped[list["Hotspot"]] = relationship(
        "Hotspot", back_populates="analysis_run", cascade="all, delete-orphan"
    )
    violations: Mapped[list["Violation"]] = relationship(
        "Violation", back_populates="analysis_run", cascade="all, delete-orphan"
    )


class FileNode(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "file_nodes"

    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    path: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    language: Mapped[str] = mapped_column(String(50), index=True, nullable=False)
    loc: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    blank_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    comment_lines: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    cyclomatic_complexity: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    afferent_coupling: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Fan-in
    efferent_coupling: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # Fan-out
    instability: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    analysis_run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="files")
    symbols: Mapped[list["Symbol"]] = relationship(
        "Symbol", back_populates="file_node", cascade="all, delete-orphan"
    )


class Symbol(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "symbols"

    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    file_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("file_nodes.id", ondelete="CASCADE"), index=True, nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    qualified_name: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    symbol_type: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )  # module, package, class, function, method, interface
    start_line: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    end_line: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    analysis_run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="symbols")
    file_node: Mapped["FileNode"] = relationship("FileNode", back_populates="symbols")


class GraphEdge(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "graph_edges"

    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_symbol_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("symbols.id", ondelete="CASCADE"), index=True, nullable=False
    )
    target_symbol_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("symbols.id", ondelete="CASCADE"), index=True, nullable=False
    )
    edge_type: Mapped[str] = mapped_column(
        String(50), index=True, nullable=False
    )  # imports, calls, inherits, implements, contains
    line_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    properties: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    analysis_run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="edges")


class GitCommit(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "git_commits"

    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    commit_sha: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    author_alias: Mapped[str] = mapped_column(String(100), index=True, nullable=False)
    authored_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    insertions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    deletions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    files_changed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    analysis_run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="commits")


class GitFileChurn(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "git_file_churns"

    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    file_path: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    commit_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lines_added: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    lines_deleted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    author_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    ownership_entropy: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)

    analysis_run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="file_churns")


class Hotspot(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "hotspots"

    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    file_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("file_nodes.id", ondelete="CASCADE"), nullable=True
    )
    file_path: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    score: Mapped[float] = mapped_column(Float, index=True, nullable=False)
    churn_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    centrality_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    complexity_score: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)

    analysis_run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="hotspots")


class Violation(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "violations"

    analysis_run_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("analysis_runs.id", ondelete="CASCADE"), index=True, nullable=False
    )
    source_file_path: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    target_file_path: Mapped[str] = mapped_column(String(1024), index=True, nullable=False)
    rule_name: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    severity: Mapped[str] = mapped_column(
        String(20), default="warning", index=True, nullable=False
    )  # error, warning, info
    message: Mapped[str] = mapped_column(Text, nullable=False)
    layer_from: Mapped[str | None] = mapped_column(String(100), nullable=True)
    layer_to: Mapped[str | None] = mapped_column(String(100), nullable=True)

    analysis_run: Mapped["AnalysisRun"] = relationship("AnalysisRun", back_populates="violations")
