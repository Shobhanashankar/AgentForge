"""
Base Agent — defines the shared interface all agents implement.
Includes exponential backoff retry logic for transient failures.
"""
import asyncio
import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class AgentStatus(str, Enum):
    SUCCESS       = "SUCCESS"
    FAILED        = "FAILED"
    NEEDS_REVISION = "NEEDS_REVISION"


@dataclass
class AgentInput:
    task_id:          str
    prompt:           str
    data:             dict        = field(default_factory=dict)
    revision_feedback: list | None = None
    revision_count:   int         = 0


@dataclass
class AgentOutput:
    agent_name:  str
    status:      AgentStatus
    data:        dict        = field(default_factory=dict)
    message:     str         = ""
    error:       str | None  = None
    duration_ms: int         = 0


class BaseAgent:
    name: str = "BaseAgent"

    # Retry configuration — override per agent if needed
    MAX_RETRIES:   int   = 3
    BASE_DELAY_S:  float = 1.0   # first retry wait
    BACKOFF_FACTOR: float = 2.0  # each retry doubles the wait

    async def run(self, input: AgentInput) -> AgentOutput:
        """
        Public entry point. Wraps _execute() with exponential backoff retry.
        On permanent failure, returns a FAILED AgentOutput instead of raising.
        """
        last_error = ""
        delay = self.BASE_DELAY_S

        for attempt in range(1, self.MAX_RETRIES + 1):
            t0 = time.monotonic()
            try:
                result = await self._execute(input)
                result.duration_ms = int((time.monotonic() - t0) * 1000)
                return result

            except Exception as exc:
                last_error = str(exc)
                duration_ms = int((time.monotonic() - t0) * 1000)

                if attempt < self.MAX_RETRIES:
                    # Log retry attempt (in production would use proper logger)
                    print(
                        f"[{self.name}] Attempt {attempt}/{self.MAX_RETRIES} failed: "
                        f"{exc!r}. Retrying in {delay:.1f}s…"
                    )
                    await asyncio.sleep(delay)
                    delay *= self.BACKOFF_FACTOR
                else:
                    print(
                        f"[{self.name}] All {self.MAX_RETRIES} attempts failed. "
                        f"Last error: {exc!r}"
                    )
                    return AgentOutput(
                        agent_name=self.name,
                        status=AgentStatus.FAILED,
                        error=f"Agent failed after {self.MAX_RETRIES} attempts: {last_error}",
                        message=f"Permanent failure: {last_error}",
                        duration_ms=duration_ms,
                    )

        # Should never reach here
        return AgentOutput(
            agent_name=self.name,
            status=AgentStatus.FAILED,
            error=last_error,
            message="Unexpected retry exhaustion.",
        )

    async def _execute(self, input: AgentInput) -> AgentOutput:
        """Override this in each concrete agent."""
        raise NotImplementedError(f"{self.name} must implement _execute()")