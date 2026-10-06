from dataclasses import dataclass, field


@dataclass
class LayerDefinition:
    name: str
    patterns: list[str]  # Glob patterns e.g. ["**/controllers/**", "*controller*"]
    description: str = ""


@dataclass
class ArchitectureRule:
    source_layer: str
    target_layer: str
    allowed: bool = False
    severity: str = "error"  # error, warning, info
    description: str = ""


@dataclass
class ArchitectureRulesConfig:
    name: str = "Standard Clean Architecture"
    layers: list[LayerDefinition] = field(default_factory=list)
    rules: list[ArchitectureRule] = field(default_factory=list)
    max_file_loc: int = 500
    max_cyclomatic_complexity: float = 20.0
    max_efferent_coupling: int = 15

    @classmethod
    def default_clean_architecture(cls) -> "ArchitectureRulesConfig":
        """Predefined standard Clean Architecture configuration."""
        layers = [
            LayerDefinition(
                name="controller",
                patterns=["**/controllers/**", "**/*controller*", "**/api/**", "**/routers/**"],
                description="Presentation and HTTP API controllers",
            ),
            LayerDefinition(
                name="service",
                patterns=["**/services/**", "**/*service*"],
                description="Core domain and business logic services",
            ),
            LayerDefinition(
                name="repository",
                patterns=["**/repositories/**", "**/*repository*"],
                description="Data access repositories",
            ),
            LayerDefinition(
                name="database",
                patterns=["**/db/**", "**/database/**", "**/*database*"],
                description="Database infrastructure and models",
            ),
        ]

        rules = [
            # Controller can call Service, but NEVER Database directly
            ArchitectureRule(
                source_layer="controller",
                target_layer="database",
                allowed=False,
                severity="error",
                description="Layer Violation: Controller cannot directly bypass Service/Repository to access Database.",
            ),
            # Repository should never call Controller
            ArchitectureRule(
                source_layer="repository",
                target_layer="controller",
                allowed=False,
                severity="error",
                description="Layer Violation: Repository layer cannot import from Presentation/Controller layer.",
            ),
            # Service should never call Controller
            ArchitectureRule(
                source_layer="service",
                target_layer="controller",
                allowed=False,
                severity="error",
                description="Layer Violation: Service layer cannot depend on Presentation/Controller layer.",
            ),
        ]

        return cls(
            name="Clean Architecture (Layered)",
            layers=layers,
            rules=rules,
        )
