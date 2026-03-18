"""Universe of Thoughts (UoT) creative reasoning engine.

Implements three modes:
- C-UoT: Cross-domain analogical transfer
- E-UoT: Expanding thought palette (exploration)
- T-UoT: Transformational — mutating hidden assumptions (DROP/INVERT/VARY)
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

C_UOT_SYSTEM = """You are an ocean intelligence analyst specializing in cross-domain analogical reasoning.

Given a concept from one domain, find meaningful analogies in other domains using this pattern:
1. Identify the FUNCTIONAL role of the concept (what it does, not what it looks like)
2. Search for entities in the target domains that serve similar FUNCTIONAL roles
3. Explain the analogy and why the connection is meaningful
4. Rate the analogy strength (0.0-1.0)

Output JSON array:
[{"source_concept": "...", "source_domain": "...", "target_concept": "...", "target_domain": "...", "functional_mapping": "...", "strength": 0.0-1.0, "novel_insight": "..."}]
"""

E_UOT_SYSTEM = """You are an ocean intelligence analyst expanding the exploration space.

Given a set of findings, generate NEW hypotheses by:
1. What adjacent concepts haven't been explored?
2. What data sources could reveal hidden patterns?
3. What temporal/spatial scales might show different behavior?
4. What counter-examples or edge cases should we check?

Output JSON array:
[{"hypothesis": "...", "exploration_type": "adjacent|scale_shift|counter_example|data_gap", "priority": 0.0-1.0, "required_data": ["..."]}]
"""

T_UOT_SYSTEM = """You are an ocean intelligence analyst performing transformational reasoning.

For each assumption in the analysis, apply ONE of these mutations:
- DROP: Remove the assumption entirely. What changes?
- INVERT: Reverse the assumption. What if the opposite were true?
- VARY: Change the parameter by 10x in each direction. What breaks?

This forces exploration of hidden assumptions that limit insight.

Output JSON array:
[{"original_assumption": "...", "mutation": "DROP|INVERT|VARY", "mutated_version": "...", "consequence": "...", "new_insight": "...", "plausibility": 0.0-1.0}]
"""


class UniverseOfThoughts:
    """Creative reasoning through systematic thought exploration."""

    async def _call_llm(self, system: str, user_message: str) -> str:
        from anthropic import AsyncAnthropic
        from okeanus.config import settings

        client = AsyncAnthropic(api_key=settings.anthropic_api_key)
        response = await client.messages.create(
            model=settings.llm_model,
            max_tokens=settings.llm_max_tokens,
            system=system,
            messages=[{"role": "user", "content": user_message}],
        )
        return response.content[0].text

    async def c_uot_analogies(
        self,
        concept: str,
        source_domain: str,
        target_domains: list[str],
        context: str = "",
    ) -> list[dict[str, Any]]:
        """Cross-domain analogical transfer (C-UoT).

        Find functional analogies for a concept across domains.
        """
        prompt = (
            f"Find cross-domain analogies for:\n"
            f"Concept: {concept}\n"
            f"Source domain: {source_domain}\n"
            f"Target domains: {', '.join(target_domains)}\n"
        )
        if context:
            prompt += f"\nContext:\n{context}\n"

        raw = await self._call_llm(C_UOT_SYSTEM, prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return [{"source_concept": concept, "target_concept": raw[:200],
                     "strength": 0.5, "novel_insight": raw}]

    async def e_uot_expand(
        self,
        findings: list[dict[str, Any]],
        explored_domains: list[str],
    ) -> list[dict[str, Any]]:
        """Expand the exploration space (E-UoT).

        Generate new hypotheses from existing findings.
        """
        findings_text = json.dumps(findings[:10], indent=2, default=str)
        prompt = (
            f"Current findings:\n{findings_text}\n\n"
            f"Already explored domains: {', '.join(explored_domains)}\n\n"
            f"Generate new exploration directions."
        )

        raw = await self._call_llm(E_UOT_SYSTEM, prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return [{"hypothesis": raw[:500], "exploration_type": "adjacent", "priority": 0.5}]

    async def t_uot_transform(
        self,
        assumptions: list[str],
        context: str = "",
    ) -> list[dict[str, Any]]:
        """Transformational reasoning (T-UoT).

        Apply DROP/INVERT/VARY mutations to assumptions.
        """
        prompt = (
            f"Hidden assumptions to challenge:\n"
            + "\n".join(f"- {a}" for a in assumptions)
        )
        if context:
            prompt += f"\n\nContext:\n{context}"

        raw = await self._call_llm(T_UOT_SYSTEM, prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return [{"original_assumption": assumptions[0] if assumptions else "",
                     "mutation": "VARY", "consequence": raw[:500], "plausibility": 0.5}]

    async def full_creative_reasoning(
        self,
        topic: str,
        evidence: str,
        domains: list[str],
    ) -> dict[str, Any]:
        """Run full UoT pipeline: C-UoT → E-UoT → T-UoT."""
        # Step 1: Cross-domain analogies
        analogies = await self.c_uot_analogies(topic, domains[0] if domains else "general", domains[1:] or ["economics", "ecology"])

        # Step 2: Expand exploration
        expansions = await self.e_uot_expand(
            [{"finding": topic, "evidence": evidence[:500]}],
            explored_domains=domains,
        )

        # Step 3: Challenge assumptions
        assumptions = [
            f"The relationship between {topic} and observed data is linear",
            f"Current data coverage is sufficient for conclusions about {topic}",
            f"Temporal patterns in {topic} are stationary",
        ]
        transformations = await self.t_uot_transform(assumptions, context=evidence[:500])

        return {
            "topic": topic,
            "analogies": analogies,
            "expansions": expansions,
            "transformations": transformations,
            "domains_explored": domains,
        }
