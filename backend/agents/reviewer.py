"""
Reviewer Agent — Scores the draft report and either approves it or
requests specific revisions. Fully dynamic — feedback is generated from
actual report content and the original query. 
First run always requests a revision to demonstrate the feedback loop;
subsequent runs approve if score >= 70.
"""
import asyncio
import random
import re
from .base import BaseAgent, AgentInput, AgentOutput, AgentStatus


def _extract_topic(prompt: str) -> str:
    topic = prompt.strip()
    for prefix in ["research", "write", "analyze", "compare", "explain", "tell me about",
                   "what is", "what are", "summarize", "investigate", "explore", "study",
                   "describe", "give me", "provide"]:
        if topic.lower().startswith(prefix):
            topic = topic[len(prefix):].strip(" .,:?")
            break
    return topic[:80].strip()


def _extract_sections_from_report(report: str) -> list[str]:
    """Pull actual section headings out of the report markdown."""
    headings = re.findall(r'^##\s+(.+)$', report, re.MULTILINE)
    return headings


def _score_report(report: str, prompt: str, revision_count: int) -> int:
    """
    Score the report based on real heuristics:
    - Length (more complete = better)
    - Topic coverage (does it mention the topic keywords?)
    - Section count
    - Revision bonus
    """
    topic = _extract_topic(prompt).lower()
    topic_words = set(topic.split())

    word_count = len(report.split())
    section_count = len(_extract_sections_from_report(report))

    # How many topic keywords appear in the report?
    report_lower = report.lower()
    keyword_hits = sum(1 for w in topic_words if w in report_lower and len(w) > 3)
    keyword_score = min(20, keyword_hits * 4)

    # Length score: 300 words = 20pts, 600+ = 40pts
    length_score = min(40, word_count // 15)

    # Section score: each section up to 5 = 5pts each
    section_score = min(25, section_count * 5)

    # Revision bonus
    revision_bonus = revision_count * 10

    base = keyword_score + length_score + section_score + revision_bonus
    noise = random.randint(-4, 4)
    return min(100, max(30, base + noise))


def _generate_feedback(report: str, prompt: str, sections: list[str]) -> list[dict]:
    """
    Generate specific, actionable feedback based on actual report sections
    and what the original query asked for.
    """
    topic = _extract_topic(prompt)
    is_comparison = any(kw in prompt.lower() for kw in ["vs", "versus", "compare", "difference"])
    feedback = []

    report_lower = report.lower()
    word_count = len(report.split())

    # Check executive summary depth
    if "executive summary" in report_lower:
        exec_start = report_lower.find("executive summary")
        exec_section = report[exec_start:exec_start + 400]
        if len(exec_section.split()) < 40:
            feedback.append({
                "section": "Executive Summary",
                "comment": f"The executive summary is too brief for a topic as nuanced as '{topic}'. "
                           f"Expand it to cover the key dimensions examined and the primary takeaway in 3–5 sentences."
            })

    # Check conclusion specificity
    if "conclusion" in report_lower:
        if topic.lower() not in report_lower[report_lower.rfind("conclusion"):]:
            feedback.append({
                "section": "Conclusion",
                "comment": f"The conclusion does not explicitly reference '{topic}'. "
                           f"Add a concrete recommendation that directly answers the original query: '{prompt}'."
            })

    # For comparison queries, check if both sides are addressed
    if is_comparison:
        parts = re.split(r'\bvs\.?\b|\bversus\b', topic, flags=re.IGNORECASE)
        if len(parts) >= 2:
            a, b = parts[0].strip().lower(), parts[1].strip().lower()
            a_word = a.split()[0] if a else ""
            b_word = b.split()[0] if b else ""
            if a_word and b_word:
                if a_word not in report_lower or b_word not in report_lower:
                    feedback.append({
                        "section": "Comparative Analysis",
                        "comment": f"The report should explicitly name and contrast both '{a}' and '{b}' "
                                   f"in each major section for a true side-by-side comparison."
                    })

    # Check for metrics / quantification
    has_numbers = bool(re.search(r'\d+%|\d+ (teams|companies|engineers|years|ms|seconds)', report_lower))
    if not has_numbers:
        target_section = sections[1] if len(sections) > 1 else "Key Findings"
        feedback.append({
            "section": target_section,
            "comment": f"Strengthen the analysis of '{topic}' by including specific metrics, "
                       f"percentages, or quantified benchmarks where possible to support the claims made."
        })

    # Check report length
    if word_count < 250:
        feedback.append({
            "section": "General",
            "comment": f"The report is too concise at {word_count} words. "
                       f"Each section covering '{topic}' should be expanded with more detail and supporting evidence."
        })

    # Return 2–3 feedback items max
    random.shuffle(feedback)
    return feedback[:3] if feedback else [
        {
            "section": "Executive Summary",
            "comment": f"Strengthen the opening by explicitly stating what makes '{topic}' significant "
                       f"and what the reader will take away from this report."
        }
    ]


class ReviewerAgent(BaseAgent):
    name = "ReviewerAgent"

    async def _execute(self, input: AgentInput) -> AgentOutput:
        await asyncio.sleep(0.9)

        report: str = input.data.get("report", "")
        original_prompt: str = input.prompt
        revision_count: int = input.revision_count
        word_count = len(report.split())

        sections = _extract_sections_from_report(report)
        score = _score_report(report, original_prompt, revision_count)

        # First run always requests revision to show the feedback loop.
        # After that, approve if score >= 70.
        approved = revision_count >= 1 and score >= 70

        feedback = []
        if not approved:
            feedback = _generate_feedback(report, original_prompt, sections)

        topic = _extract_topic(original_prompt)
        summary = (
            f"The report on '{topic}' is comprehensive and addresses the query effectively."
            if approved else
            f"The report on '{topic}' needs targeted improvements before it meets the quality bar."
        )

        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.SUCCESS if approved else AgentStatus.NEEDS_REVISION,
            data={
                "approved": approved,
                "score": score,
                "feedback": feedback,
                "summary": summary,
                "word_count_assessed": word_count,
                "revision_count": revision_count,
            },
            message=(
                f"Report approved. Score: {score}/100. {summary}"
                if approved else
                f"Revision requested. Score: {score}/100. {len(feedback)} issue(s) found. {summary}"
            ),
        )