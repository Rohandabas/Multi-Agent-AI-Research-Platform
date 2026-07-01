"""
CostTracker — tracks token usage and cost per agent and per session.
Stores to DB via LLMCallLog. Shown in the frontend UI.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Optional

from app.config.constants import (
    GEMINI_FLASH_INPUT_PRICE_PER_1M,
    GEMINI_FLASH_OUTPUT_PRICE_PER_1M,
)


@dataclass
class AgentCost:
    agent: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    duration_seconds: float = 0.0
    timestamp: float = field(default_factory=time.time)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


class CostTracker:
    """
    Tracks LLM costs across all agents in a research session.
    Persists to DB at the end of the pipeline.
    """

    def __init__(self):
        self._agent_costs: list[AgentCost] = []

    def record(
        self,
        agent: str,
        model: str,
        input_tokens: int,
        output_tokens: int,
        duration_seconds: float = 0.0,
    ) -> AgentCost:
        """Record a single LLM call."""
        cost = self._calculate_cost(model, input_tokens, output_tokens)
        entry = AgentCost(
            agent=agent,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
            duration_seconds=duration_seconds,
        )
        self._agent_costs.append(entry)
        return entry

    def record_from_result(self, agent_result, model: str = "gemini-2.0-flash") -> Optional[AgentCost]:
        """Record from an AgentResult dataclass."""
        if not agent_result or not agent_result.tokens_used:
            return None
        return self.record(
            agent=agent_result.agent,
            model=model,
            input_tokens=agent_result.tokens_used // 2,
            output_tokens=agent_result.tokens_used // 2,
            duration_seconds=agent_result.duration_seconds,
        )

    @property
    def total_input_tokens(self) -> int:
        return sum(c.input_tokens for c in self._agent_costs)

    @property
    def total_output_tokens(self) -> int:
        return sum(c.output_tokens for c in self._agent_costs)

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def total_cost_usd(self) -> float:
        return round(sum(c.cost_usd for c in self._agent_costs), 6)

    def get_summary(self) -> dict:
        """Get full session cost summary."""
        by_agent = {}
        for c in self._agent_costs:
            if c.agent not in by_agent:
                by_agent[c.agent] = {
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost_usd": 0.0,
                }
            by_agent[c.agent]["input_tokens"] += c.input_tokens
            by_agent[c.agent]["output_tokens"] += c.output_tokens
            by_agent[c.agent]["cost_usd"] += c.cost_usd

        return {
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_tokens": self.total_tokens,
            "total_cost_usd": self.total_cost_usd,
            "by_agent": by_agent,
        }

    def to_db_records(self, report_id: str) -> list[dict]:
        """Convert to format for DB persistence."""
        return [
            {
                "report_id": report_id,
                "agent": c.agent,
                "model": c.model,
                "input_tokens": c.input_tokens,
                "output_tokens": c.output_tokens,
                "cost_usd": c.cost_usd,
                "duration_seconds": c.duration_seconds,
            }
            for c in self._agent_costs
        ]

    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        from app.config.constants import (
            GEMINI_FLASH_INPUT_PRICE_PER_1M,
            GEMINI_FLASH_OUTPUT_PRICE_PER_1M,
            GROQ_LLAMA_INPUT_PRICE_PER_1M,
            GROQ_LLAMA_OUTPUT_PRICE_PER_1M,
        )
        model_lower = model.lower()
        if "llama" in model_lower or "mixtral" in model_lower or "groq" in model_lower:
            input_cost = (input_tokens / 1_000_000) * GROQ_LLAMA_INPUT_PRICE_PER_1M
            output_cost = (output_tokens / 1_000_000) * GROQ_LLAMA_OUTPUT_PRICE_PER_1M
        else:
            input_cost = (input_tokens / 1_000_000) * GEMINI_FLASH_INPUT_PRICE_PER_1M
            output_cost = (output_tokens / 1_000_000) * GEMINI_FLASH_OUTPUT_PRICE_PER_1M
        return round(input_cost + output_cost, 8)
