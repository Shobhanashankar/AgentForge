"""
Planner Agent — Decomposes the user prompt into ordered, dependency-mapped sub-tasks.
Returns a structured list that the Researcher and Orchestrator consume.
"""
import asyncio
import re
from typing import Optional
from .base import BaseAgent, AgentInput, AgentOutput, AgentStatus


def _build_plan(prompt: str, template_key: str) -> list:
    """Dynamically inject the user's topic into every subtask title and description."""
    p = prompt.strip()

    # Extract a short topic label from the prompt
    # e.g. "Research the pros and cons of microservices vs monoliths" -> "microservices vs monoliths"
    topic = p
    for prefix in ["research", "write", "analyze", "compare", "explain", "tell me about",
                   "what is", "what are", "summarize", "investigate", "explore", "study"]:
        if topic.lower().startswith(prefix):
            topic = topic[len(prefix):].strip(" .,:")
            break
    topic = topic[:80].strip()  # cap length

    if template_key == "comparison":
        # Try to extract the two things being compared
        parts = re.split(r'\bvs\.?\b|\bversus\b|\bor\b|\band\b', topic, flags=re.IGNORECASE)
        a = parts[0].strip().title() if len(parts) > 0 else "Option A"
        b = parts[1].strip().title() if len(parts) > 1 else "Option B"
        return [
            {
                "id": "t1",
                "title": f"Define {a} and {b}",
                "description": f"Clearly define and characterize {a} and {b}, including their core principles and origins.",
                "order": 1,
                "dependencies": [],
            },
            {
                "id": "t2",
                "title": f"Technical Analysis of {a} vs {b}",
                "description": f"Deep-dive into the architecture, performance, and scalability differences between {a} and {b}.",
                "order": 2,
                "dependencies": ["t1"],
            },
            {
                "id": "t3",
                "title": f"Pros & Cons: {a} vs {b}",
                "description": f"Map out the strengths and weaknesses of {a} and {b} side-by-side.",
                "order": 3,
                "dependencies": ["t1"],
            },
            {
                "id": "t4",
                "title": f"Industry Adoption of {a} and {b}",
                "description": f"Research real-world adoption rates, community sentiment, and future trends for {a} and {b}.",
                "order": 4,
                "dependencies": [],
            },
            {
                "id": "t5",
                "title": f"When to Choose {a} vs {b}",
                "description": f"Establish a decision framework: criteria and scenarios where {a} or {b} is the better choice.",
                "order": 5,
                "dependencies": ["t2", "t3", "t4"],
            },
        ]

    elif template_key == "research":
        return [
            {
                "id": "t1",
                "title": f"Define the Problem: {topic}",
                "description": f"Precisely define the problem space of '{topic}' and explain why it matters.",
                "order": 1,
                "dependencies": [],
            },
            {
                "id": "t2",
                "title": f"Current State of the Art in {topic}",
                "description": f"Survey existing solutions, approaches, and tools related to '{topic}'.",
                "order": 2,
                "dependencies": ["t1"],
            },
            {
                "id": "t3",
                "title": f"Key Findings & Insights on {topic}",
                "description": f"Extract the most important discoveries and insights from research on '{topic}'.",
                "order": 3,
                "dependencies": ["t2"],
            },
            {
                "id": "t4",
                "title": f"Implications & Impact of {topic}",
                "description": f"Analyze the practical implications and broader societal or technical impact of '{topic}'.",
                "order": 4,
                "dependencies": ["t3"],
            },
        ]

    else:  # default
        return [
            {
                "id": "t1",
                "title": f"Background & Context: {topic}",
                "description": f"Gather foundational background information and historical context on '{topic}'.",
                "order": 1,
                "dependencies": [],
            },
            {
                "id": "t2",
                "title": f"Advantages & Benefits of {topic}",
                "description": f"Research the key advantages, benefits, and positive aspects of '{topic}'.",
                "order": 2,
                "dependencies": ["t1"],
            },
            {
                "id": "t3",
                "title": f"Disadvantages & Challenges of {topic}",
                "description": f"Research the key drawbacks, risks, and challenges associated with '{topic}'.",
                "order": 3,
                "dependencies": ["t1"],
            },
            {
                "id": "t4",
                "title": f"Real-World Use Cases of {topic}",
                "description": f"Find concrete real-world examples and use cases that demonstrate '{topic}' in practice.",
                "order": 4,
                "dependencies": ["t2", "t3"],
            },
            {
                "id": "t5",
                "title": f"Conclusion & Recommendations on {topic}",
                "description": f"Synthesize findings on '{topic}' into actionable conclusions and recommendations.",
                "order": 5,
                "dependencies": ["t4"],
            },
        ]


def _pick_template(prompt: str) -> str:
    lower = prompt.lower()
    if any(kw in lower for kw in ["vs", "versus", "compare", "difference", "pros and cons", "which is better"]):
        return "comparison"
    if any(kw in lower for kw in ["research", "study", "investigate", "analyze", "explore"]):
        return "research"
    return "default"


class PlannerAgent(BaseAgent):
    name = "PlannerAgent"

    async def _execute(self, input: AgentInput) -> AgentOutput:
        await asyncio.sleep(0.8)  # simulate processing time

        template_key = _pick_template(input.prompt)
        subtasks = _build_plan(input.prompt, template_key)

        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.SUCCESS,
            data={
                "subtasks": subtasks,
                "template_used": template_key,
                "total_subtasks": len(subtasks),
            },
            message=f"Decomposed into {len(subtasks)} sub-tasks using '{template_key}' plan.",
        )