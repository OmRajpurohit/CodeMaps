from abc import ABC, abstractmethod
from typing import Any

import httpx

from backend.app.core.config import settings
from backend.app.core.logging import logger


class BaseLLMClient(ABC):
    """Abstract interface for LLM reasoning providers."""

    @abstractmethod
    async def generate_explanation(self, user_question: str, dossier: dict[str, Any]) -> str:
        """
        Synthesizes an architectural explanation strictly grounded in the provided Evidence Dossier.
        Prohibited from inventing or hallucinating metrics or graph edges.
        """
        pass


class MockLLMClient(BaseLLMClient):
    """
    Deterministic rule-based synthesizer.
    Generates structured, professional architectural reasoning directly from verified facts.
    """

    async def generate_explanation(self, user_question: str, dossier: dict[str, Any]) -> str:
        component = dossier.get("file_path", "Target Component")
        metrics = dossier.get("metrics", {})
        hotspots = dossier.get("hotspots", [])
        violations = dossier.get("violations", [])
        blast_radius = dossier.get("blast_radius", {})
        churn = dossier.get("churn", {})

        fan_in = metrics.get("fan_in", 0)
        fan_out = metrics.get("fan_out", 0)
        loc = metrics.get("loc", 0)
        complexity = metrics.get("cyclomatic_complexity", 1.0)
        instability = metrics.get("instability", 0.0)
        commits = churn.get("commit_count", 0)

        lines: list[str] = [
            f"### Architectural Analysis & Risk Assessment: `{component}`\n",
            f"**Inquiry:** {user_question}\n",
            "#### 1. Verified Evidence & Metrics",
            f"- **Lines of Code (LOC):** {loc}",
            f"- **Cyclomatic Complexity:** {complexity:.1f}",
            f"- **Afferent Coupling (Fan-In):** {fan_in} dependent modules",
            f"- **Efferent Coupling (Fan-Out):** {fan_out} external dependencies",
            f"- **Instability Metric ($I$):** {instability:.2f} (where 0.0 = completely stable core, 1.0 = purely unstable)",
            f"- **Git Evolution Churn:** {commits} commits modifying this module",
        ]

        if blast_radius:
            direct_dep = blast_radius.get("direct_dependents_count", 0)
            trans_dep = blast_radius.get("transitive_dependents_count", 0)
            score = blast_radius.get("impact_score", 0.0)
            lines.extend([
                "\n#### 2. Change Impact & Blast Radius",
                f"- **Direct Dependents:** {direct_dep}",
                f"- **Transitive Dependents:** {trans_dep}",
                f"- **Calculated Blast Radius Score:** {score:.1f} / 100.0",
            ])

        if violations:
            lines.append("\n#### 3. Architectural Layer Violations")
            for v in violations:
                lines.append(f"- ⚠️ **[{v.get('severity', 'warning').upper()}]** {v.get('message')}")
        else:
            lines.append("\n#### 3. Architectural Rules Compliance\n- ✅ No architectural layer boundary violations detected.")

        if hotspots:
            top_h = hotspots[0]
            lines.extend([
                "\n#### 4. Hotspot Rationale",
                f"- **Risk Score:** {top_h.get('score', 0):.1f} / 100.0",
                f"- **Rationale:** {top_h.get('rationale')}",
            ])

        lines.extend([
            "\n#### 5. Architectural Recommendation",
            "Based on the deterministic dependency structure, any modification to this module should follow strict regression testing given its upstream dependents.",
        ])

        return "\n".join(lines)


class OpenAILLMClient(BaseLLMClient):
    """OpenAI GPT provider with strict grounding prompt."""

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    async def generate_explanation(self, user_question: str, dossier: dict[str, Any]) -> str:
        prompt = (
            "You are a principal software architect. You are provided with a verified, deterministic "
            "Evidence Dossier of a codebase component. You must strictly ground your answer in these facts. "
            "Never invent graph edges or hallucinate metrics.\n\n"
            f"Evidence Dossier: {dossier}\n\n"
            f"User Question: {user_question}\n"
        )
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.2,
                    },
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data["choices"][0]["message"]["content"]
                return f"LLM API Error ({resp.status_code}): {resp.text}"
        except Exception as e:
            logger.warning("LLM request failed, falling back to deterministic synthesizer: %s", str(e))
            return await MockLLMClient().generate_explanation(user_question, dossier)


def get_llm_client() -> BaseLLMClient:
    """Factory creating LLM client based on configuration."""
    if settings.LLM_PROVIDER == "openai" and settings.OPENAI_API_KEY:
        return OpenAILLMClient(settings.OPENAI_API_KEY)
    return MockLLMClient()
