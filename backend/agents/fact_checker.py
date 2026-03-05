"""
FactCheckerAgent — agent that scans the draft report for
unverified claims and annotates them. Only runs if enable_fact_check=True.
"""
import asyncio
import random
import re
from .base import BaseAgent, AgentInput, AgentOutput, AgentStatus


class FactCheckerAgent(BaseAgent):
    name = "FactCheckerAgent"

    async def _execute(self, input: AgentInput) -> AgentOutput:
        await asyncio.sleep(0.6)

        report: str = input.data.get("report", "")
        prompt: str = input.prompt

        # Extract sentences that contain numbers or strong claims
        sentences = re.split(r'(?<=[.!?])\s+', report)
        flagged = []
        verified = []

        for sent in sentences:
            sent = sent.strip()
            if not sent or len(sent) < 20:
                continue
            has_number = bool(re.search(r'\d+%|\d+x|\d+ (engineers|companies|teams|years)', sent, re.IGNORECASE))
            has_claim  = any(kw in sent.lower() for kw in ["always", "never", "all", "every", "proven", "guaranteed"])

            if has_number or has_claim:
                # Simulate verification: 80% pass, 20% flagged
                if random.random() < 0.2:
                    flagged.append({
                        "claim":  sent[:120],
                        "reason": "Contains a quantitative claim that could not be independently verified.",
                        "severity": "low",
                    })
                else:
                    verified.append(sent[:80])

        status = AgentStatus.SUCCESS
        annotations = {
            "flagged_claims": flagged,
            "verified_count": len(verified),
            "flagged_count":  len(flagged),
            "overall_credibility": "high" if len(flagged) == 0 else "medium" if len(flagged) <= 2 else "low",
        }

        return AgentOutput(
            agent_name=self.name,
            status=status,
            data=annotations,
            message=(
                f"Fact check complete: {len(verified)} claim(s) verified, {len(flagged)} flagged."
            ),
        )