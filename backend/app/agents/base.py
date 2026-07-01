"""
BaseAgent — the abstract base class every agent inherits from.

Features:
  - Dependency injection (tools passed via __init__)
  - Structured logging via AgentLogger
  - Async retry with exponential backoff
  - Progress broadcasting via job_manager
  - Standardized AgentResult return type
"""
from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from typing import Any, Optional, TYPE_CHECKING

from app.schemas.response import AgentResult
from app.logging.logger import AgentLogger
from app.errors.base import ResearchException

if TYPE_CHECKING:
    from app.graph.state import ResearchState
    from app.services.job_manager import JobManager


class BaseAgent(ABC):
    """
    Abstract base for all research agents.

    Subclass pattern:
        class SearchAgent(BaseAgent):
            def __init__(self, config, search_tool: BaseSearchTool):
                super().__init__(config, tools={"search": search_tool})

            async def _execute(self, state) -> AgentResult:
                ...
    """

    # Override in subclasses
    agent_name: str = "BaseAgent"

    def __init__(self, config: Any, tools: dict = None, job_manager: "JobManager" = None):
        self.config = config
        self.tools = tools or {}
        self.job_manager = job_manager
        self._logger: Optional[AgentLogger] = None

    # ─── Abstract ─────────────────────────────────────────────────────────────

    @abstractmethod
    async def _execute(self, state: "ResearchState") -> AgentResult:
        """Core agent logic. Must return an AgentResult."""
        ...

    # ─── Public run() ─────────────────────────────────────────────────────────

    async def run(self, state: "ResearchState") -> AgentResult:
        """
        Execute the agent with retry logic and structured logging.
        This is what LangGraph calls — never override this.
        """
        job_id = state.get("job_id", "")
        self._logger = AgentLogger(self.agent_name, job_id)
        self._logger.started()

        # Broadcast start event
        await self._broadcast("agent_start", f"{self.agent_name} started...", state)

        start_time = time.time()

        for attempt in range(1, self.config.max_retries + 1):
            try:
                result = await self._execute(state)
                duration = time.time() - start_time

                self._logger.finished(
                    tokens_input=result.tokens_used // 2,
                    tokens_output=result.tokens_used // 2,
                    cost_usd=result.cost_usd,
                )

                await self._broadcast("agent_complete", f"{self.agent_name} completed", state)
                return result

            except ResearchException as e:
                self._logger.error(e.message, e)
                if attempt == self.config.max_retries:
                    await self._broadcast("agent_error", f"{self.agent_name} failed: {e.message}", state)
                    return AgentResult(
                        success=False,
                        agent=self.agent_name,
                        data=None,
                        duration_seconds=time.time() - start_time,
                        error=e.message,
                        retries=attempt - 1,
                    )
                self._logger.retry(attempt, str(e))
                await asyncio.sleep(2 ** attempt)

            except Exception as e:
                self._logger.error(str(e), e)
                if attempt == self.config.max_retries:
                    await self._broadcast("agent_error", f"{self.agent_name} failed: {str(e)}", state)
                    return AgentResult(
                        success=False,
                        agent=self.agent_name,
                        data=None,
                        duration_seconds=time.time() - start_time,
                        error=str(e),
                        retries=attempt - 1,
                    )
                self._logger.retry(attempt, str(e))
                await asyncio.sleep(2 ** attempt)

        # Should never reach here
        return AgentResult(
            success=False,
            agent=self.agent_name,
            data=None,
            duration_seconds=time.time() - start_time,
            error="Max retries exceeded",
        )

    # ─── Progress broadcasting ────────────────────────────────────────────────

    async def _broadcast(self, event: str, message: str, state: "ResearchState", data: dict = None):
        """Broadcast a WebSocket progress event."""
        if self.job_manager:
            from app.schemas.response import ProgressEvent
            progress_event = ProgressEvent(
                event=event,
                agent=self.agent_name,
                message=message,
                progress=state.get("progress_pct", 0),
                cost_so_far=state.get("total_cost_usd", 0.0),
                data=data,
            )
            await self.job_manager.broadcast(state.get("job_id", ""), progress_event)

    # ─── Logging shortcuts ────────────────────────────────────────────────────

    def log_info(self, message: str):
        if self._logger:
            self._logger.info(message)

    def log_warning(self, message: str):
        if self._logger:
            self._logger.warning(message)

    def log_error(self, message: str, exc: Exception = None):
        if self._logger:
            self._logger.error(message, exc)
