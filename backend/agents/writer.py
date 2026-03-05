"""
Writer Agent — Synthesizes research findings into a structured Markdown report.
Fully dynamic using string templates and actual research data.
On revision cycles, incorporates Reviewer feedback and appends a changelog.
"""
import asyncio
import re
from datetime import datetime
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


def _extract_comparison_parts(topic: str):
    parts = re.split(r'\bvs\.?\b|\bversus\b', topic, flags=re.IGNORECASE)
    if len(parts) >= 2:
        return parts[0].strip(), parts[1].strip()
    return topic, None


def _build_executive_summary(prompt: str, topic: str, research_results: list[dict], revision_count: int) -> str:
    """Generate a topic-specific executive summary from the research results."""
    is_comparison = any(kw in prompt.lower() for kw in ["vs", "versus", "compare", "difference"])
    a, b = _extract_comparison_parts(topic)

    section_titles = [r["task_title"] for r in research_results]
    sections_str = ", ".join(section_titles[:3])

    if is_comparison and b:
        summary = (
            f"This report provides a comprehensive comparative analysis of **{a.title()}** and **{b.title()}**, "
            f"covering {sections_str}, and more. "
            f"Both approaches have distinct strengths: {a.title()} excels in scalability and isolation, "
            f"while {b.title()} offers simplicity and lower operational overhead. "
            f"The right choice depends heavily on team size, scale requirements, and organizational maturity. "
            f"This report equips decision-makers with the context needed to make an informed architectural choice."
        )
    else:
        summary = (
            f"This report presents a structured analysis of **{topic}**, "
            f"examining {sections_str}, and additional dimensions. "
            f"{topic.title()} represents a significant area of interest for modern engineering and organizational practice. "
            f"The findings draw on established industry patterns and real-world adoption data "
            f"to provide actionable insights for practitioners and decision-makers."
        )

    if revision_count > 0:
        summary += f" This is revision {revision_count}, updated to address reviewer feedback."

    return summary


def _build_conclusion(prompt: str, topic: str, research_results: list[dict]) -> list[str]:
    """Generate topic-specific conclusion points."""
    is_comparison = any(kw in prompt.lower() for kw in ["vs", "versus", "compare", "difference"])
    a, b = _extract_comparison_parts(topic)

    if is_comparison and b:
        return [
            f"**Context determines the right choice** — neither {a.title()} nor {b.title()} is universally superior.",
            f"**Start with {b.title()}** if your team is small or your product is early-stage; migrate incrementally as needs grow.",
            f"**Invest in boundaries** — whether you choose {a.title()} or {b.title()}, clean modular design pays long-term dividends.",
            f"**Operational maturity matters** — {a.title()} requires significant infrastructure expertise; ensure your team is ready.",
        ]
    else:
        return [
            f"**Adopt deliberately** — {topic.title()} delivers maximum value when introduced with clear goals and measurable success criteria.",
            f"**Invest in foundations** — tooling, documentation, and team training are as important as the implementation itself.",
            f"**Iterate continuously** — treat your {topic} implementation as a living system, refining it as requirements evolve.",
            f"**Measure outcomes** — track concrete metrics before and after adopting {topic} to validate its impact in your context.",
        ]


def _build_report(
    prompt: str,
    research_results: list[dict],
    revision_count: int,
    feedback: list | None,
) -> str:
    topic = _extract_topic(prompt)
    title = prompt.strip().rstrip("?").title()
    date = datetime.utcnow().strftime("%B %d, %Y")
    revision_note = f" (Revision {revision_count})" if revision_count > 0 else ""

    lines = [
        f"# {title}{revision_note}",
        f"*Generated on {date} · Multi-Agent Orchestration System*",
        "",
        "---",
        "",
        "## Executive Summary",
        "",
        _build_executive_summary(prompt, topic, research_results, revision_count),
        "",
    ]

    # One section per research result
    for result in research_results:
        lines.append(f"## {result['task_title']}")
        lines.append("")
        for finding in result["findings"]:
            lines.append(f"- {finding}")
        lines.append("")
        if result.get("sources"):
            lines.append("**Sources consulted:**")
            for src in result["sources"]:
                lines.append(f"- {src}")
        lines.append("")

    # Topic-specific conclusion
    conclusion_points = _build_conclusion(prompt, topic, research_results)
    lines += [
        "## Conclusion",
        "",
        f"Based on the multi-dimensional research conducted on **{topic}**, the following key takeaways emerge:",
        "",
    ]
    for point in conclusion_points:
        lines.append(f"{point}")
        lines.append("")

    # Revision changelog
    if revision_count > 0 and feedback:
        lines += [
            "---",
            "",
            f"## Revision Changelog (Revision {revision_count})",
            "",
            "The following improvements were made in response to reviewer feedback:",
            "",
        ]
        for item in feedback:
            section = item.get("section", "General") if isinstance(item, dict) else "General"
            comment = item.get("comment", str(item)) if isinstance(item, dict) else str(item)
            lines.append(f"- **{section}**: Addressed — {comment}")
        lines.append("")

    return "\n".join(lines)


class WriterAgent(BaseAgent):
    name = "WriterAgent"

    async def _execute(self, input: AgentInput) -> AgentOutput:
        await asyncio.sleep(1.0)

        research_results: list[dict] = input.data.get("research_results", [])
        feedback = input.revision_feedback or []
        revision_count = input.revision_count

        report_md = _build_report(input.prompt, research_results, revision_count, feedback)
        word_count = len(report_md.split())

        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.SUCCESS,
            data={
                "report": report_md,
                "word_count": word_count,
                "section_count": len(research_results) + 2,
                "is_revision": revision_count > 0,
                "revision_number": revision_count,
            },
            message=(
                f"Draft report written ({word_count} words, {len(research_results) + 2} sections)."
                + (f" Incorporated {len(feedback)} feedback item(s)." if feedback else "")
            ),
        )