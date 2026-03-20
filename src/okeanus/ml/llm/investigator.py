"""Recursive investigation engine — spawns sub-tasks with fresh Claude contexts.

Inspired by ReDel (arXiv 2408.02248) and Palantir AIP Agent Studio.
Adds 3 meta-tools on top of the existing 12 data tools to enable
multi-step, evidence-chained ocean intelligence investigations.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any

from pydantic import BaseModel

from okeanus.config import settings

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


class InvestigationStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Finding(BaseModel):
    id: str
    task_id: str
    claim: str
    evidence_type: str  # data_query, analytics, correlation, inference
    source_data: dict[str, Any]
    confidence: float  # 0.0–1.0
    tools_used: list[str]


class InvestigationTask(BaseModel):
    id: str
    investigation_id: str
    parent_task_id: str | None
    question: str
    acceptance_criteria: str
    status: InvestigationStatus
    depth: int
    findings: list[Finding]
    sub_task_ids: list[str]
    llm_messages: list[dict]
    created_at: datetime
    completed_at: datetime | None = None


class InvestigationReport(BaseModel):
    summary: str
    key_findings: list[Finding]
    evidence_chains: list[dict]
    recommendations: list[str]
    data_gaps: list[str]
    confidence: float
    total_tool_calls: int
    total_tasks: int


class Investigation(BaseModel):
    id: str
    question: str
    status: InvestigationStatus
    max_depth: int
    created_at: datetime
    updated_at: datetime
    root_task_id: str | None = None
    tasks: dict[str, InvestigationTask] = {}
    report: InvestigationReport | None = None
    progress_log: list[dict] = []


# ---------------------------------------------------------------------------
# In-memory store
# ---------------------------------------------------------------------------

_investigations: dict[str, Investigation] = {}


def get_investigation(investigation_id: str) -> Investigation | None:
    return _investigations.get(investigation_id)


# ---------------------------------------------------------------------------
# Meta-tool definitions (appended to the 12 data tools)
# ---------------------------------------------------------------------------

META_TOOL_DEFINITIONS = [
    {
        "name": "create_sub_investigation",
        "description": (
            "Spawn a sub-investigation to answer a specific sub-question. "
            "The sub-investigation runs autonomously with its own tool-use loop "
            "and returns its findings. Use this to break complex questions into "
            "focused, parallel sub-tasks."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "question": {
                    "type": "string",
                    "description": "The specific sub-question to investigate",
                },
                "acceptance_criteria": {
                    "type": "string",
                    "description": "What constitutes a satisfactory answer",
                },
            },
            "required": ["question", "acceptance_criteria"],
        },
    },
    {
        "name": "record_finding",
        "description": (
            "Record a verified finding with evidence. Use this after you have "
            "queried data and confirmed a claim. Every important conclusion "
            "should be recorded as a finding."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "claim": {
                    "type": "string",
                    "description": "The factual claim being recorded",
                },
                "evidence_type": {
                    "type": "string",
                    "enum": ["data_query", "analytics", "correlation", "inference"],
                    "description": "Type of evidence supporting the claim",
                },
                "source_data": {
                    "type": "object",
                    "description": "The tool results/data that support this claim",
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence level 0.0–1.0",
                },
            },
            "required": ["claim", "evidence_type", "confidence"],
        },
    },
    {
        "name": "get_sibling_findings",
        "description": (
            "Retrieve findings from sibling investigation tasks (other sub-investigations "
            "at the same level). Useful for cross-referencing and avoiding duplicate work."
        ),
        "input_schema": {
            "type": "object",
            "properties": {},
        },
    },
]


# ---------------------------------------------------------------------------
# Investigator system prompt template
# ---------------------------------------------------------------------------

INVESTIGATOR_PROMPT = """You are an ocean intelligence investigator conducting a focused research task.
You have access to 95+ ocean data sources through your tools, covering physical oceanography, vessel tracking, marine biology, satellite imagery, blue economy data, and analytics.

**Your current task:**
- Question: {question}
- Acceptance criteria: {acceptance_criteria}
- Investigation ID: {investigation_id}
- Task depth: {depth}/{max_depth}
- Remaining sub-investigation depth: {remaining_depth}

**Strategy:**
1. Start by using data query tools to gather relevant evidence
2. Use analytics tools to identify patterns, trends, and anomalies
3. Record each verified finding using record_finding with appropriate confidence scores
4. If a sub-question needs deep exploration, use create_sub_investigation to spawn a child task
5. Use get_sibling_findings to cross-reference with parallel sub-task results
6. When you have enough evidence, provide your final synthesis

**Rules:**
- Only record findings backed by actual data from your tools
- Set confidence based on data quality and coverage (0.0–1.0)
- Create sub-investigations for questions needing focused exploration
- Don't create sub-investigations if you can answer directly with a few tool calls
- Maximum {remaining_depth} more levels of sub-investigation allowed (0 = no more sub-tasks)
- Be thorough but efficient — aim for 3-8 findings per task
"""


# ---------------------------------------------------------------------------
# Investigation engine
# ---------------------------------------------------------------------------


class InvestigationEngine:
    """Runs a recursive investigation with Claude tool-use."""

    # Max chars per tool result (~12K tokens).  Keeps total context well
    # within 1M even at 15 iterations with multiple tool calls each.
    TOOL_RESULT_MAX_CHARS = 50_000

    def __init__(self, investigation: Investigation):
        self.investigation = investigation
        self._client = None
        self._total_tool_calls = 0

    @staticmethod
    def _truncate_tool_result(result: Any, max_chars: int) -> str:
        """Truncate a tool result string to *max_chars*.

        When the result is a dict containing an ``items`` or ``features``
        list (the common pattern from data-query tools), keep only the
        first entries that fit and append a short summary so the LLM
        knows data was trimmed.
        """
        import json

        text = str(result)
        if len(text) <= max_chars:
            return text

        # Try to truncate at the data level for cleaner output
        if isinstance(result, dict):
            for key in ("items", "features", "nodes", "regions", "sources"):
                if key in result and isinstance(result[key], list):
                    total = len(result[key])
                    # Binary-search for how many items fit
                    lo, hi = 0, total
                    while lo < hi:
                        mid = (lo + hi + 1) // 2
                        candidate = {**result, key: result[key][:mid]}
                        candidate["_truncated"] = f"Showing {mid}/{total} {key}"
                        if "count" in candidate:
                            candidate["count"] = f"{mid}/{total}"
                        if len(json.dumps(candidate, default=str)) <= max_chars:
                            lo = mid
                        else:
                            hi = mid - 1
                    if lo > 0:
                        truncated = {**result, key: result[key][:lo]}
                        truncated["_truncated"] = f"Showing {lo}/{total} {key}. Ask for more specific filters to narrow results."
                        if "count" in truncated:
                            truncated["count"] = f"{lo}/{total}"
                        return json.dumps(truncated, default=str)

        # Fallback: hard character truncation
        return text[:max_chars] + f"\n... [TRUNCATED — {len(text):,} chars total, showing first {max_chars:,}]"

    @property
    def client(self):
        if self._client is None:
            import anthropic

            self._client = anthropic.AsyncAnthropic(api_key=settings.anthropic_api_key)
        return self._client

    async def run(self) -> None:
        """Main entry point — creates root task, runs it, synthesizes report."""
        self.investigation.status = InvestigationStatus.RUNNING
        self.investigation.updated_at = datetime.now(timezone.utc)
        self._log("investigation_started", None, f"Starting: {self.investigation.question}")

        try:
            # Create root task
            root_task = self._create_task(
                question=self.investigation.question,
                acceptance_criteria="Provide a comprehensive, evidence-based answer to the question.",
                parent_task_id=None,
                depth=0,
            )
            self.investigation.root_task_id = root_task.id

            # Run root task (which may spawn sub-tasks recursively)
            await self._run_task(root_task)

            # Synthesize final report
            self._log("synthesizing", None, "All tasks complete, synthesizing report...")
            report = await self._synthesize_report()
            self.investigation.report = report
            self.investigation.status = InvestigationStatus.COMPLETED

        except Exception as exc:
            logger.exception("Investigation %s failed", self.investigation.id)
            self.investigation.status = InvestigationStatus.FAILED
            self._log("error", None, f"Investigation failed: {exc}")

        self.investigation.updated_at = datetime.now(timezone.utc)
        self._log("investigation_complete", None, f"Status: {self.investigation.status.value}")

    def _create_task(
        self,
        question: str,
        acceptance_criteria: str,
        parent_task_id: str | None,
        depth: int,
    ) -> InvestigationTask:
        """Create a new investigation task."""
        task = InvestigationTask(
            id=str(uuid.uuid4()),
            investigation_id=self.investigation.id,
            parent_task_id=parent_task_id,
            question=question,
            acceptance_criteria=acceptance_criteria,
            status=InvestigationStatus.PENDING,
            depth=depth,
            findings=[],
            sub_task_ids=[],
            llm_messages=[],
            created_at=datetime.now(timezone.utc),
        )
        self.investigation.tasks[task.id] = task
        self._log("task_created", task.id, f"Depth {depth}: {question[:100]}")
        return task

    async def _run_task(self, task: InvestigationTask) -> None:
        """Run a single investigation task with Claude tool-use loop."""
        from okeanus.ml.llm.tools import TOOL_DEFINITIONS, execute_tool

        task.status = InvestigationStatus.RUNNING
        self._log("task_started", task.id, f"Running: {task.question[:80]}")

        remaining_depth = self.investigation.max_depth - task.depth
        system_prompt = INVESTIGATOR_PROMPT.format(
            question=task.question,
            acceptance_criteria=task.acceptance_criteria,
            investigation_id=self.investigation.id,
            depth=task.depth,
            max_depth=self.investigation.max_depth,
            remaining_depth=remaining_depth,
        )

        # Combine data tools + meta tools
        all_tools = TOOL_DEFINITIONS + META_TOOL_DEFINITIONS

        # Initial user message
        task.llm_messages.append({
            "role": "user",
            "content": (
                f"Investigate: {task.question}\n\n"
                f"Acceptance criteria: {task.acceptance_criteria}\n\n"
                "Begin by querying relevant data, then record your findings."
            ),
        })

        tools_used: list[str] = []
        max_iterations = 15

        for iteration in range(max_iterations):
            try:
                response = await self.client.messages.create(
                    model=settings.llm_model,
                    max_tokens=settings.llm_max_tokens,
                    system=system_prompt,
                    messages=task.llm_messages,
                    tools=all_tools,
                )
            except Exception as exc:
                logger.error("LLM call failed for task %s: %s", task.id, exc)
                self._log("llm_error", task.id, str(exc))
                break

            if response.stop_reason == "tool_use":
                task.llm_messages.append({"role": "assistant", "content": response.content})

                tool_results: list[dict[str, Any]] = []
                for block in response.content:
                    if block.type != "tool_use":
                        continue

                    tool_name = block.name
                    tools_used.append(tool_name)
                    self._total_tool_calls += 1

                    try:
                        if tool_name in ("create_sub_investigation", "record_finding", "get_sibling_findings"):
                            result = await self._execute_meta_tool(
                                tool_name, block.input, task
                            )
                        else:
                            result = await execute_tool(tool_name, block.input)

                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": self._truncate_tool_result(
                                result, self.TOOL_RESULT_MAX_CHARS
                            ),
                        })
                    except Exception as exc:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": f"Error: {exc}",
                            "is_error": True,
                        })

                task.llm_messages.append({"role": "user", "content": tool_results})
            else:
                # Final text response — task is done
                task.llm_messages.append({"role": "assistant", "content": response.content})
                break

        task.status = InvestigationStatus.COMPLETED
        task.completed_at = datetime.now(timezone.utc)
        self._log(
            "task_completed",
            task.id,
            f"Findings: {len(task.findings)}, Tools: {len(tools_used)}",
        )

    async def _execute_meta_tool(
        self,
        name: str,
        params: dict[str, Any],
        task: InvestigationTask,
    ) -> dict[str, Any]:
        """Handle the 3 meta-tools."""

        if name == "create_sub_investigation":
            remaining_depth = self.investigation.max_depth - task.depth
            if remaining_depth <= 0:
                return {
                    "error": "Maximum investigation depth reached. "
                    "Answer this question directly using data tools."
                }

            child = self._create_task(
                question=params["question"],
                acceptance_criteria=params["acceptance_criteria"],
                parent_task_id=task.id,
                depth=task.depth + 1,
            )
            task.sub_task_ids.append(child.id)

            # Run child task (sequential to avoid rate limits)
            await self._run_task(child)

            # Return summary of child's findings
            findings_summary = []
            for f in child.findings:
                findings_summary.append({
                    "claim": f.claim,
                    "confidence": f.confidence,
                    "evidence_type": f.evidence_type,
                })

            return {
                "sub_task_id": child.id,
                "status": child.status.value,
                "findings_count": len(child.findings),
                "findings": findings_summary,
            }

        elif name == "record_finding":
            finding = Finding(
                id=str(uuid.uuid4()),
                task_id=task.id,
                claim=params["claim"],
                evidence_type=params["evidence_type"],
                source_data=params.get("source_data", {}),
                confidence=max(0.0, min(1.0, params["confidence"])),
                tools_used=[],
            )
            task.findings.append(finding)
            self._log(
                "finding_recorded",
                task.id,
                f"[{finding.confidence:.0%}] {finding.claim[:100]}",
            )
            return {"recorded": True, "finding_id": finding.id}

        elif name == "get_sibling_findings":
            siblings: list[dict] = []
            for t in self.investigation.tasks.values():
                if t.id == task.id:
                    continue
                if t.parent_task_id == task.parent_task_id:
                    for f in t.findings:
                        siblings.append({
                            "task_question": t.question[:80],
                            "claim": f.claim,
                            "confidence": f.confidence,
                            "evidence_type": f.evidence_type,
                        })
            return {"sibling_findings": siblings, "count": len(siblings)}

        return {"error": f"Unknown meta-tool: {name}"}

    async def _synthesize_report(self) -> InvestigationReport:
        """Synthesize all findings into a final report using Claude."""
        all_findings: list[Finding] = []
        for task in self.investigation.tasks.values():
            all_findings.extend(task.findings)

        if not all_findings:
            return InvestigationReport(
                summary="No findings were recorded during the investigation.",
                key_findings=[],
                evidence_chains=[],
                recommendations=["Try a more specific question or verify data availability."],
                data_gaps=["Investigation produced no findings."],
                confidence=0.0,
                total_tool_calls=self._total_tool_calls,
                total_tasks=len(self.investigation.tasks),
            )

        # Build findings text for Claude
        findings_text = ""
        for i, f in enumerate(all_findings, 1):
            task = self.investigation.tasks.get(f.task_id)
            task_q = task.question[:80] if task else "unknown"
            findings_text += (
                f"\n{i}. [{f.evidence_type}] (confidence: {f.confidence:.0%}) "
                f"Task: {task_q}\n"
                f"   Claim: {f.claim}\n"
            )

        # Task tree summary
        task_tree = ""
        for t in self.investigation.tasks.values():
            indent = "  " * t.depth
            task_tree += (
                f"{indent}- [{t.status.value}] {t.question[:80]} "
                f"({len(t.findings)} findings)\n"
            )

        synthesis_prompt = f"""Synthesize these investigation findings into a structured report.

**Original question:** {self.investigation.question}

**Task tree:**
{task_tree}

**All findings ({len(all_findings)}):**
{findings_text}

Produce a JSON response with these fields:
- "summary": 2-4 paragraph executive summary
- "key_findings": list of the most important finding claims (strings)
- "evidence_chains": list of objects showing how findings connect (each: {{"from": "claim1", "to": "claim2", "relationship": "supports/contradicts/extends"}})
- "recommendations": list of actionable next steps
- "data_gaps": list of data that was missing or unavailable
- "confidence": overall confidence score 0.0-1.0

Return ONLY the JSON object, no markdown formatting."""

        try:
            response = await self.client.messages.create(
                model=settings.llm_model,
                max_tokens=settings.llm_max_tokens,
                messages=[{"role": "user", "content": synthesis_prompt}],
            )

            import json

            text = ""
            for block in response.content:
                if hasattr(block, "text"):
                    text += block.text

            # Parse JSON response — handle possible markdown wrapping
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()

            data = json.loads(text)

            # Build key findings as Finding objects
            key_finding_objects = []
            key_claims = data.get("key_findings", [])
            for claim in key_claims:
                # Match to actual findings
                for f in all_findings:
                    if f.claim in str(claim) or str(claim) in f.claim:
                        key_finding_objects.append(f)
                        break

            return InvestigationReport(
                summary=data.get("summary", ""),
                key_findings=key_finding_objects[:10],
                evidence_chains=data.get("evidence_chains", []),
                recommendations=data.get("recommendations", []),
                data_gaps=data.get("data_gaps", []),
                confidence=float(data.get("confidence", 0.5)),
                total_tool_calls=self._total_tool_calls,
                total_tasks=len(self.investigation.tasks),
            )

        except Exception as exc:
            logger.error("Report synthesis failed: %s", exc)
            return InvestigationReport(
                summary=f"Synthesis failed ({exc}). Raw findings available below.",
                key_findings=sorted(all_findings, key=lambda f: f.confidence, reverse=True)[:10],
                evidence_chains=[],
                recommendations=[],
                data_gaps=[],
                confidence=0.0,
                total_tool_calls=self._total_tool_calls,
                total_tasks=len(self.investigation.tasks),
            )

    def _log(self, event: str, task_id: str | None, message: str) -> None:
        """Append to investigation progress log."""
        entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "event": event,
            "task_id": task_id,
            "message": message,
        }
        self.investigation.progress_log.append(entry)
        logger.info("Investigation %s [%s] %s", self.investigation.id[:8], event, message)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def start_investigation(
    question: str,
    max_depth: int = 3,
) -> Investigation:
    """Create and launch an investigation in the background."""
    investigation = Investigation(
        id=str(uuid.uuid4()),
        question=question,
        status=InvestigationStatus.PENDING,
        max_depth=min(max_depth, settings.investigation_max_depth),
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    _investigations[investigation.id] = investigation

    # Run in background
    engine = InvestigationEngine(investigation)
    asyncio.create_task(engine.run())

    return investigation
