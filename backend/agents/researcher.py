"""
Researcher Agent — Processes each sub-task and returns structured findings.
Fully dynamic using string templates and the actual topic/query.
Independent sub-tasks (no dependencies on pending tasks) are run concurrently.
"""
import asyncio
import random
import re
from .base import BaseAgent, AgentInput, AgentOutput, AgentStatus


def _extract_topic(prompt: str) -> str:
    """Pull the core topic out of the user's prompt."""
    topic = prompt.strip()
    for prefix in ["research", "write", "analyze", "compare", "explain", "tell me about",
                   "what is", "what are", "summarize", "investigate", "explore", "study",
                   "describe", "give me", "provide"]:
        if topic.lower().startswith(prefix):
            topic = topic[len(prefix):].strip(" .,:?")
            break
    return topic[:80].strip()


def _extract_comparison_parts(topic: str):
    """For comparison queries, extract the two sides."""
    parts = re.split(r'\bvs\.?\b|\bversus\b', topic, flags=re.IGNORECASE)
    if len(parts) >= 2:
        return parts[0].strip().strip("'\""), parts[1].strip().strip("'\"")
    return topic, None


def _generate_findings(task_title: str, task_description: str, topic: str, original_prompt: str) -> list[str]:
    """
    Generate 4 dynamic, topic-specific findings by interpolating the real topic
    into pattern templates based on the sub-task type.
    """
    lower_title = task_title.lower()
    lower_prompt = original_prompt.lower()

    is_comparison = any(kw in lower_prompt for kw in ["vs", "versus", "compare", "difference"])
    a, b = _extract_comparison_parts(topic)
    b = b or "alternative approaches"

    # Background / Define / Context
    if any(k in lower_title for k in ["background", "context", "define", "definition", "overview", "introduction"]):
        return [
            f"{topic.title()} has evolved significantly over the past two decades, becoming a foundational concept in its domain.",
            f"The term '{topic}' refers to a structured approach that addresses core challenges in the field, with roots in both academic research and industry practice.",
            f"Early adoption of {topic} was driven by the need to solve scalability and maintainability problems that simpler approaches could not address.",
            f"Today, {topic} is recognized as a best practice by major industry bodies and is covered extensively in technical literature and standards.",
        ]

    # Advantages / Benefits / Pros
    if any(k in lower_title for k in ["advantage", "benefit", "pros", "strength", "positive"]):
        if is_comparison:
            return [
                f"{a.title()} offers strong isolation of concerns, making it easier to develop, test, and deploy individual components independently.",
                f"Teams working with {a.title()} report faster iteration cycles because changes in one area do not require full-system coordination.",
                f"{a.title()} enables technology flexibility — different components can use the best-fit tools and languages for their specific requirements.",
                f"Fault tolerance is a key strength of {a.title()}: a failure in one component does not cascade to bring down the entire system.",
            ]
        return [
            f"One of the primary advantages of {topic} is its ability to reduce complexity by providing clear boundaries and separation of concerns.",
            f"{topic.title()} significantly improves maintainability — teams report up to 40% reduction in time spent debugging and fixing regressions.",
            f"Adopting {topic} enables better scalability: systems can grow incrementally without requiring wholesale architectural rewrites.",
            f"Organizations using {topic} consistently report improved team productivity and faster onboarding of new engineers.",
        ]

    # Disadvantages / Challenges / Cons
    if any(k in lower_title for k in ["disadvantage", "challenge", "risk", "cons", "drawback", "limitation", "weakness"]):
        if is_comparison:
            return [
                f"{a.title()} introduces distributed system complexity — network latency, partial failures, and consistency trade-offs become real concerns.",
                f"Operational overhead with {a.title()} is substantially higher: teams need expertise in orchestration, service discovery, and distributed tracing.",
                f"Data consistency across boundaries inherent in {a.title()} requires careful design patterns such as sagas or event sourcing.",
                f"Developer onboarding is more demanding with {a.title()} — understanding a distributed system takes significantly longer than a single codebase.",
            ]
        return [
            f"The primary challenge with {topic} is the upfront investment required: proper implementation demands careful planning and architectural discipline.",
            f"{topic.title()} can introduce overhead in small teams or early-stage projects where the added structure slows initial velocity.",
            f"Without clear governance, {topic} can lead to inconsistent implementations across teams, undermining the intended benefits.",
            f"Tooling and infrastructure requirements for {topic} add operational complexity that must be factored into total cost of ownership.",
        ]

    # Use Cases / Examples / Adoption
    if any(k in lower_title for k in ["use case", "example", "adoption", "case study", "application", "industry", "real-world"]):
        if is_comparison:
            return [
                f"Large-scale platforms pioneered the use of {a.title()}, demonstrating its viability at extreme scale with hundreds of independent components.",
                f"Startups and small teams frequently prefer {b.title()} in early stages, citing faster initial development and simpler deployment pipelines.",
                f"Industry surveys show that 65% of companies with over 500 engineers use {a.title()}, while smaller teams lean toward {b.title()}.",
                f"A notable counter-example: several companies have migrated back from {a.title()} to {b.title()} after finding the operational complexity outweighed the benefits at their scale.",
            ]
        return [
            f"Leading technology companies have successfully applied {topic} in production environments serving millions of users globally.",
            f"A notable case study involves a Fortune 500 company that adopted {topic} and reduced deployment failures by 60% within the first year.",
            f"Open-source communities have built robust tooling around {topic}, accelerating adoption across startups and enterprises alike.",
            f"Academic and industry research consistently validates {topic} as effective across diverse domains including finance, healthcare, and e-commerce.",
        ]

    # Conclusion / Recommendations / Decision Framework
    if any(k in lower_title for k in ["conclusion", "recommendation", "decision", "framework", "when to", "choose", "summary"]):
        if is_comparison:
            return [
                f"The choice between {a.title()} and {b.title()} is fundamentally context-dependent: team size, traffic scale, and operational maturity all play a role.",
                f"For teams with fewer than 10 engineers or products in early stages, {b.title()} typically delivers better ROI due to lower operational overhead.",
                f"At scale — high traffic, large teams, or strong isolation requirements — {a.title()} provides compelling advantages that justify its complexity.",
                f"A recommended starting point is {b.title()} with clean internal module boundaries, allowing gradual migration to {a.title()} as requirements become clear.",
            ]
        return [
            f"Based on available evidence, {topic} is most effective when implemented with clear ownership, documented conventions, and iterative refinement.",
            f"Organizations should assess their specific constraints — team size, traffic, and timeline — before committing to a {topic} implementation strategy.",
            f"The optimal approach to {topic} combines proven patterns from the literature with pragmatic adaptations to local context and constraints.",
            f"Long-term success with {topic} depends on continuous investment in tooling, documentation, and team education rather than one-time adoption.",
        ]

    # Technical Analysis
    if any(k in lower_title for k in ["technical", "architecture", "performance", "scalability", "analysis"]):
        if is_comparison:
            return [
                f"Architecturally, {a.title()} distributes state and logic across independent units, while {b.title()} centralizes them in a single deployable artifact.",
                f"Performance benchmarks show {a.title()} adds measurable network overhead per inter-service call — a trade-off that matters at high request volumes.",
                f"{b.title()} benefits from in-process communication and shared memory, yielding lower latency for tightly coupled operations.",
                f"Scalability profiles differ: {a.title()} allows per-component scaling, while {b.title()} requires scaling the entire application for isolated bottlenecks.",
            ]
        return [
            f"The technical architecture of {topic} is built on well-established principles including separation of concerns and single responsibility.",
            f"Performance characteristics of {topic} are well-studied: under typical workloads, overhead is minimal relative to the organizational benefits gained.",
            f"Scalability is a core design goal of {topic}: the architecture supports horizontal scaling without fundamental redesign.",
            f"Integration with modern tooling — CI/CD pipelines, monitoring systems, and cloud platforms — is well-supported in {topic} implementations.",
        ]

    # Implications / Impact / Future
    if any(k in lower_title for k in ["implication", "impact", "effect", "consequence", "future", "trend"]):
        return [
            f"The broader impact of {topic} extends beyond technical teams — it influences organizational structure, hiring practices, and product strategy.",
            f"Industry adoption of {topic} is accelerating: analyst reports project continued growth as more organizations recognize its long-term value.",
            f"Emerging trends suggest {topic} will increasingly integrate with AI-driven tooling, automation, and cloud-native infrastructure.",
            f"The societal implications of widespread {topic} adoption include faster software delivery, improved reliability, and reduced system downtime.",
        ]

    # Current State / State of the Art
    if any(k in lower_title for k in ["state of the art", "current", "existing", "survey", "landscape"]):
        return [
            f"The current landscape of {topic} is characterized by a rich ecosystem of tools, frameworks, and established best practices.",
            f"Recent surveys indicate that over 70% of engineering organizations are actively using or evaluating {topic} in some form.",
            f"Key players in the {topic} space include both open-source communities and commercial vendors offering managed solutions.",
            f"The state of the art in {topic} continues to advance rapidly, with new patterns and tooling emerging from both academia and industry.",
        ]

    # Generic fallback
    return [
        f"Research into '{task_title}' reveals that {topic} is a well-established area with substantial literature and real-world validation.",
        f"Key practitioners in the field of {topic} emphasize the importance of context-specific application over rigid rule-following.",
        f"Empirical studies on {topic} consistently demonstrate measurable improvements in quality, efficiency, or reliability when properly applied.",
        f"The sub-topic of '{task_title}' within {topic} is actively evolving, with new insights emerging from ongoing industry experience.",
    ]


def _generate_sources(task_id: str, topic: str) -> list[str]:
    slug = topic.lower().replace(" ", "-")[:30]
    return [
        f"https://research.example.com/{slug}/{task_id}",
        f"https://docs.industry-standard.org/topics/{slug}",
    ]


async def _research_single_task(task: dict, original_prompt: str) -> dict:
    await asyncio.sleep(random.uniform(0.4, 1.0))
    topic = _extract_topic(original_prompt)
    findings = _generate_findings(
        task_title=task["title"],
        task_description=task.get("description", ""),
        topic=topic,
        original_prompt=original_prompt,
    )
    return {
        "task_id": task["id"],
        "task_title": task["title"],
        "findings": findings,
        "sources": _generate_sources(task["id"], topic),
        "confidence": round(random.uniform(0.78, 0.96), 2),
    }


class ResearcherAgent(BaseAgent):
    name = "ResearcherAgent"

    async def _execute(self, input: AgentInput) -> AgentOutput:
        subtasks: list[dict] = input.data.get("subtasks", [])
        original_prompt: str = input.prompt

        completed_ids: set[str] = set()
        all_results: list[dict] = []
        waves: list[list[dict]] = []

        remaining = list(subtasks)
        while remaining:
            wave = [t for t in remaining if all(dep in completed_ids for dep in t.get("dependencies", []))]
            if not wave:
                wave = [remaining[0]]
            waves.append(wave)
            for t in wave:
                completed_ids.add(t["id"])
            remaining = [t for t in remaining if t not in wave]

        for wave in waves:
            wave_results = await asyncio.gather(
                *[_research_single_task(t, original_prompt) for t in wave]
            )
            all_results.extend(wave_results)

        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.SUCCESS,
            data={
                "research_results": all_results,
                "waves_executed": len(waves),
                "total_tasks_researched": len(all_results),
            },
            message=f"Completed {len(all_results)} research tasks across {len(waves)} execution wave(s).",
        )