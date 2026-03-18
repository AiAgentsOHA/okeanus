"""PRefLexOR reasoning pipeline — Think, Reflect, Refine with adversarial critique.

Implements the Preference-based Recursive Language Modeling for Exploratory
Optimization of Reasoning (PRefLexOR) framework (Buehler, arXiv:2410.12375).

Key improvements over scaffold:
- Critic returns structured numeric scores per dimension
- Convergence loop: iterates until score delta < threshold or max_cycles
- Refiner receives both text critique AND numeric scores
- Every intermediate cycle's trace is persisted
- CAN/CANNOT/PREDICT with confidence intervals, not point estimates
"""

from __future__ import annotations

import json
import logging
import math
from typing import Any

logger = logging.getLogger(__name__)

# -- Scoring dimensions --
SCORE_DIMENSIONS = ["evidence_quality", "logical_coherence", "novelty", "actionability"]

GENERATOR_SYSTEM = """You are an ocean intelligence analyst (Generator).
Given evidence from multiple data sources, produce a structured analysis.

For each finding:
1. State the finding clearly
2. Classify it: CAN (actionable insight), CANNOT (acknowledged limitation), or PREDICT (testable hypothesis)
3. Cite specific data sources and values
4. Rate confidence as a range [low, high] between 0.0-1.0
5. Explain your reasoning chain

Output JSON array:
[{
  "finding": "...",
  "classification": "CAN|CANNOT|PREDICT",
  "confidence_low": 0.0,
  "confidence_high": 1.0,
  "sources": ["..."],
  "reasoning": "...",
  "falsifiable_prediction": "..."
}]"""

CRITIC_SYSTEM = """You are an ocean intelligence critic (Adversarial Reviewer).
You MUST be genuinely adversarial — steelman the opposition, don't rubber-stamp.

For each finding, evaluate on four dimensions (0.0-1.0 each):
- evidence_quality: Is the claim well-supported by cited data? (0=no evidence, 1=conclusive)
- logical_coherence: Does the reasoning chain hold? (0=fallacious, 1=airtight)
- novelty: Is this a genuine insight or a restatement? (0=obvious, 1=truly novel)
- actionability: Can someone act on this? (0=vague, 1=immediately actionable)

Also evaluate:
- Alternative explanations the generator missed
- Whether confidence intervals are calibrated (too wide = useless, too narrow = overconfident)
- Missing context that would change the conclusion

Output JSON array:
[{
  "finding_index": 0,
  "scores": {
    "evidence_quality": 0.0,
    "logical_coherence": 0.0,
    "novelty": 0.0,
    "actionability": 0.0
  },
  "composite_score": 0.0,
  "issues": ["..."],
  "alternative_explanations": ["..."],
  "confidence_calibration": "too_narrow|calibrated|too_wide",
  "verdict": "accept|revise|reject",
  "suggested_revision": "..."
}]"""

REFINER_SYSTEM = """You are an ocean intelligence synthesizer (Refiner).
Given the Generator's findings, the Critic's structured scores, and the Critic's text review,
produce a refined analysis.

Rules:
1. Accept findings with composite_score >= 0.7
2. Revise findings with composite_score 0.4-0.7, incorporating ALL critic feedback
3. Reject findings with composite_score < 0.4 (note as discarded with reason)
4. Adjust confidence intervals based on calibration feedback
5. Ensure CAN/CANNOT/PREDICT classifications are accurate:
   - CAN: evidence_quality >= 0.6 AND logical_coherence >= 0.6
   - CANNOT: any dimension < 0.3, or critic identified fatal flaw
   - PREDICT: novelty >= 0.5 AND has falsifiable_prediction
6. Widen confidence intervals for findings with alternative explanations
7. Narrow confidence intervals for findings with strong evidence convergence

Output JSON:
{
  "refined_findings": [
    {
      "finding": "...",
      "classification": "CAN|CANNOT|PREDICT",
      "confidence_low": 0.0,
      "confidence_high": 1.0,
      "scores": {"evidence_quality": 0.0, "logical_coherence": 0.0, "novelty": 0.0, "actionability": 0.0},
      "sources": ["..."],
      "reasoning": "...",
      "falsifiable_prediction": "..."
    }
  ],
  "discarded": [{"finding": "...", "reason": "...", "composite_score": 0.0}],
  "meta": {
    "generator_count": 0,
    "accepted": 0,
    "revised": 0,
    "rejected": 0,
    "avg_composite_score": 0.0
  }
}"""


def _composite_score(scores: dict[str, float]) -> float:
    """Weighted average of dimension scores. Evidence and coherence weighted higher."""
    weights = {
        "evidence_quality": 0.35,
        "logical_coherence": 0.30,
        "novelty": 0.20,
        "actionability": 0.15,
    }
    total = sum(scores.get(d, 0.0) * weights[d] for d in SCORE_DIMENSIONS)
    return round(total, 4)


def _avg_composite(critiques: list[dict[str, Any]]) -> float:
    """Average composite score across all critiques in a cycle."""
    if not critiques:
        return 0.0
    scores = [c.get("composite_score", 0.0) for c in critiques]
    return sum(scores) / len(scores)


class PRefLexOR:
    """Recursive thinking -> reflection -> refinement pipeline with convergence."""

    def __init__(
        self,
        max_cycles: int = 5,
        convergence_threshold: float = 0.05,
    ) -> None:
        self._max_cycles = max_cycles
        self._convergence_threshold = convergence_threshold

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
        """Critic phase — adversarial review with structured numeric scores."""
        return await self._call_llm(
            CRITIC_SYSTEM,
            f"Review these findings critically. Be genuinely adversarial:\n{findings}",
        )

    async def refine(
        self,
        findings: str,
        critique: str,
        scores_summary: str,
    ) -> str:
        """Refiner phase — synthesize using Generator output + Critic text + numeric scores."""
        prompt = (
            f"Generator findings:\n{findings}\n\n"
            f"Critic scores summary:\n{scores_summary}\n\n"
            f"Critic detailed review:\n{critique}"
        )
        return await self._call_llm(REFINER_SYSTEM, prompt)

    def _parse_critique_scores(self, critique_raw: str) -> list[dict[str, Any]]:
        """Extract structured scores from critic output."""
        try:
            parsed = json.loads(critique_raw)
            if isinstance(parsed, list):
                # Ensure composite_score is computed if missing
                for item in parsed:
                    if "scores" in item and "composite_score" not in item:
                        item["composite_score"] = _composite_score(item["scores"])
                return parsed
        except json.JSONDecodeError:
            pass
        # Fallback: return a single neutral critique
        return [{"finding_index": 0, "scores": {d: 0.5 for d in SCORE_DIMENSIONS},
                 "composite_score": 0.5, "issues": ["Could not parse structured critique"],
                 "verdict": "revise"}]

    def _scores_summary(self, critiques: list[dict[str, Any]]) -> str:
        """Build a text summary of numeric scores for the refiner."""
        lines = []
        for c in critiques:
            idx = c.get("finding_index", "?")
            scores = c.get("scores", {})
            composite = c.get("composite_score", 0.0)
            verdict = c.get("verdict", "?")
            lines.append(
                f"Finding {idx}: composite={composite:.2f} "
                f"[ev={scores.get('evidence_quality', 0):.2f} "
                f"lc={scores.get('logical_coherence', 0):.2f} "
                f"nv={scores.get('novelty', 0):.2f} "
                f"ac={scores.get('actionability', 0):.2f}] "
                f"verdict={verdict}"
            )
        avg = _avg_composite(critiques)
        lines.append(f"\nAverage composite: {avg:.3f}")
        return "\n".join(lines)

    async def run_pipeline(
        self,
        evidence: str,
        session=None,
        insight_id=None,
    ) -> dict[str, Any]:
        """Run the full PRefLexOR pipeline with convergence detection.

        Think -> [Reflect -> Refine] x N until convergence or max_cycles.
        Every intermediate cycle is traced and persisted.
        """
        traces: list[dict[str, Any]] = []
        score_history: list[float] = []

        # Phase 1: Think (Generate)
        findings = await self.think(evidence)
        traces.append({
            "phase": "generate",
            "cycle": 0,
            "input": evidence[:500],
            "output": findings,
        })

        converged = False
        final_critiques: list[dict[str, Any]] = []

        for cycle in range(self._max_cycles):
            # Phase 2: Reflect (Critique with structured scores)
            critique_raw = await self.reflect(findings)
            critiques = self._parse_critique_scores(critique_raw)
            final_critiques = critiques
            cycle_score = _avg_composite(critiques)
            score_history.append(cycle_score)

            traces.append({
                "phase": "reflect",
                "cycle": cycle,
                "input": findings[:500],
                "output": critique_raw,
                "scores": {c.get("finding_index", i): c.get("scores", {})
                           for i, c in enumerate(critiques)},
                "avg_composite": cycle_score,
            })

            # Convergence check: stop if score delta is below threshold
            if len(score_history) >= 2:
                delta = abs(score_history[-1] - score_history[-2])
                if delta < self._convergence_threshold:
                    converged = True
                    logger.info(
                        "PRefLexOR converged at cycle %d (delta=%.4f < %.4f)",
                        cycle, delta, self._convergence_threshold,
                    )
                    # Still run final refinement
                    scores_summary = self._scores_summary(critiques)
                    refined = await self.refine(findings, critique_raw, scores_summary)
                    traces.append({
                        "phase": "refine",
                        "cycle": cycle,
                        "input": f"cycle_{cycle}_converged",
                        "output": refined,
                        "avg_composite": cycle_score,
                    })
                    findings = refined
                    break

            # Phase 3: Refine with scores
            scores_summary = self._scores_summary(critiques)
            refined = await self.refine(findings, critique_raw, scores_summary)
            traces.append({
                "phase": "refine",
                "cycle": cycle,
                "input": f"cycle_{cycle}",
                "output": refined,
                "avg_composite": cycle_score,
            })

            findings = refined  # feed back for next cycle

        # Store ALL traces if session provided
        if session and insight_id:
            try:
                from okeanus.ml.synthesis.insights import InsightManager
                mgr = InsightManager()
                for t in traces:
                    await mgr.add_trace(
                        session, insight_id, t["phase"],
                        t["input"], t["output"],
                    )
            except Exception as exc:
                logger.warning("Failed to store reasoning traces: %s", exc)

        # Parse final output
        result: dict[str, Any] = {
            "raw_output": findings,
            "traces": traces,
            "cycles_run": len(score_history),
            "max_cycles": self._max_cycles,
            "converged": converged,
            "score_history": score_history,
            "final_scores": {
                c.get("finding_index", i): c.get("scores", {})
                for i, c in enumerate(final_critiques)
            },
        }

        try:
            parsed = json.loads(findings)
            if isinstance(parsed, dict) and "refined_findings" in parsed:
                result["findings"] = parsed["refined_findings"]
                result["meta"] = parsed.get("meta", {})
            elif isinstance(parsed, list):
                result["findings"] = parsed
        except json.JSONDecodeError:
            result["findings"] = [{
                "finding": findings,
                "classification": "PREDICT",
                "confidence_low": 0.2,
                "confidence_high": 0.6,
            }]

        return result

    async def classify_claim(
        self,
        claim: str,
        evidence: str,
    ) -> dict[str, Any]:
        """Classify a single claim as CAN/CANNOT/PREDICT with confidence interval.

        Uses a single-cycle Think->Reflect to produce structured classification.
        """
        prompt = (
            f"Classify this claim based on the evidence.\n\n"
            f"Claim: {claim}\n\nEvidence: {evidence}\n\n"
            f"Respond with JSON: {{"
            f'"classification": "CAN|CANNOT|PREDICT", '
            f'"confidence_low": 0.0, "confidence_high": 1.0, '
            f'"scores": {{"evidence_quality": 0.0, "logical_coherence": 0.0, '
            f'"novelty": 0.0, "actionability": 0.0}}, '
            f'"reasoning": "..."}}'
        )
        raw = await self._call_llm(GENERATOR_SYSTEM, prompt)

        # Run critic on the classification
        critique_raw = await self.reflect(raw)
        critiques = self._parse_critique_scores(critique_raw)

        try:
            result = json.loads(raw)
        except json.JSONDecodeError:
            result = {
                "classification": "PREDICT",
                "confidence_low": 0.2,
                "confidence_high": 0.5,
                "reasoning": raw,
            }

        # Overlay critic scores
        if critiques:
            result["critic_scores"] = critiques[0].get("scores", {})
            result["composite_score"] = critiques[0].get("composite_score", 0.0)
            # Adjust classification based on critic scores
            scores = critiques[0].get("scores", {})
            if scores.get("evidence_quality", 0) < 0.3 or scores.get("logical_coherence", 0) < 0.3:
                result["classification"] = "CANNOT"
            elif scores.get("evidence_quality", 0) >= 0.6 and scores.get("logical_coherence", 0) >= 0.6:
                result["classification"] = "CAN"

        return result
