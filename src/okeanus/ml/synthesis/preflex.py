"""PRefLexOR reasoning pipeline — Think, Reflect, Refine with adversarial critique.

Implements the Preference-based Recursive Language Modeling for Exploratory
Optimization of Reasoning (PRefLexOR) framework. Each claim gets classified
as CAN (actionable), CANNOT (limitation), or PREDICT (hypothesis).
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)

GENERATOR_SYSTEM = """You are an ocean intelligence analyst (Generator).
Given evidence from multiple data sources, produce a structured analysis.

For each finding:
1. State the finding clearly
2. Classify it: CAN (actionable insight), CANNOT (acknowledged limitation), or PREDICT (testable hypothesis)
3. Cite specific data sources and values
4. Rate confidence 0.0-1.0

Output JSON array:
[{"finding": "...", "classification": "CAN|CANNOT|PREDICT", "confidence": 0.0-1.0, "sources": ["..."], "reasoning": "..."}]
"""

CRITIC_SYSTEM = """You are an ocean intelligence critic (Adversarial Reviewer).
Review the Generator's findings for:
1. Logical consistency
2. Evidence sufficiency — is the claim well-supported?
3. Alternative explanations — what else could explain this?
4. Overconfidence — is the confidence justified?
5. Missing context — what data would strengthen/weaken this?

For each finding, provide:
- revised_confidence: your adjusted confidence (0.0-1.0)
- issues: list of problems found
- verdict: "accept", "revise", or "reject"

Output JSON array:
[{"finding_index": 0, "revised_confidence": 0.0-1.0, "issues": ["..."], "verdict": "accept|revise|reject", "suggested_revision": "..."}]
"""

REFINER_SYSTEM = """You are an ocean intelligence synthesizer (Refiner).
Given the Generator's findings and the Critic's review, produce the final refined analysis.

Rules:
1. Accept findings the Critic approved
2. Revise findings the Critic flagged for revision, incorporating the feedback
3. Drop findings the Critic rejected (note them as discarded)
4. Adjust confidence scores based on Critic's feedback
5. Ensure CAN/CANNOT/PREDICT classifications are accurate

Output JSON:
{"refined_findings": [...], "discarded": [...], "meta": {"generator_count": N, "accepted": N, "revised": N, "rejected": N}}
"""


class PRefLexOR:
    """Recursive thinking → reflection → refinement pipeline."""

    def __init__(self, max_cycles: int = 2) -> None:
        self._max_cycles = max_cycles

    async def _call_llm(self, system: str, user_message: str) -> str:
        """Call Claude with a specific system prompt."""
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

    async def think(self, evidence: str) -> str:
        """Generator phase — produce initial findings from evidence."""
        return await self._call_llm(GENERATOR_SYSTEM, evidence)

    async def reflect(self, findings: str) -> str:
        """Critic phase — adversarial review of findings."""
        return await self._call_llm(CRITIC_SYSTEM, f"Review these findings:\n{findings}")

    async def refine(self, findings: str, critique: str) -> str:
        """Refiner phase — synthesize Generator + Critic into final output."""
        prompt = f"Generator findings:\n{findings}\n\nCritic review:\n{critique}"
        return await self._call_llm(REFINER_SYSTEM, prompt)

    async def run_pipeline(
        self,
        evidence: str,
        session=None,
        insight_id=None,
    ) -> dict[str, Any]:
        """Run the full PRefLexOR pipeline: Think → Reflect → Refine.

        Optionally records reasoning traces to the database.
        """
        traces = []

        # Phase 1: Think (Generate)
        findings = await self.think(evidence)
        traces.append({"phase": "generate", "input": evidence[:500], "output": findings})

        for cycle in range(self._max_cycles):
            # Phase 2: Reflect (Critique)
            critique = await self.reflect(findings)
            traces.append({"phase": "reflect", "input": findings[:500], "output": critique})

            # Phase 3: Refine
            refined = await self.refine(findings, critique)
            traces.append({"phase": "refine", "input": f"cycle_{cycle}", "output": refined})

            findings = refined  # feed back for next cycle

        # Store traces if session provided
        if session and insight_id:
            try:
                from okeanus.ml.synthesis.insights import InsightManager
                mgr = InsightManager()
                for t in traces:
                    await mgr.add_trace(session, insight_id, t["phase"], t["input"], t["output"])
            except Exception as exc:
                logger.warning("Failed to store reasoning traces: %s", exc)

        # Parse final output
        result = {
            "raw_output": findings,
            "traces": traces,
            "cycles": self._max_cycles,
        }

        try:
            parsed = json.loads(findings)
            if isinstance(parsed, dict) and "refined_findings" in parsed:
                result["findings"] = parsed["refined_findings"]
                result["meta"] = parsed.get("meta", {})
            elif isinstance(parsed, list):
                result["findings"] = parsed
        except json.JSONDecodeError:
            result["findings"] = [{"finding": findings, "classification": "PREDICT", "confidence": 0.5}]

        return result

    async def classify_claim(self, claim: str, evidence: str) -> dict[str, Any]:
        """Classify a single claim as CAN/CANNOT/PREDICT with confidence."""
        prompt = f"Classify this claim based on the evidence.\n\nClaim: {claim}\n\nEvidence: {evidence}\n\nRespond with JSON: {{\"classification\": \"CAN|CANNOT|PREDICT\", \"confidence\": 0.0-1.0, \"reasoning\": \"...\"}}"
        raw = await self._call_llm(GENERATOR_SYSTEM, prompt)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"classification": "PREDICT", "confidence": 0.3, "reasoning": raw}
