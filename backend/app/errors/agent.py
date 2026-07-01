"""
Agent-related exceptions.
"""
from app.errors.base import ResearchException


class AgentException(ResearchException):
    """Base for all agent-related errors."""
    error_code = "AGENT_ERROR"


class PlannerException(AgentException):
    error_code = "PLANNER_ERROR"

    def __init__(self, reason: str):
        super().__init__(f"Planner failed: {reason}", {"reason": reason})


class ExtractionException(AgentException):
    error_code = "EXTRACTION_ERROR"

    def __init__(self, reason: str):
        super().__init__(f"Extraction failed: {reason}", {"reason": reason})


class WriterException(AgentException):
    error_code = "WRITER_ERROR"

    def __init__(self, reason: str):
        super().__init__(f"Writer failed: {reason}", {"reason": reason})


class ChartException(AgentException):
    error_code = "CHART_ERROR"

    def __init__(self, reason: str):
        super().__init__(f"Chart generation failed: {reason}", {"reason": reason})


class FactCheckException(AgentException):
    error_code = "FACT_CHECK_ERROR"

    def __init__(self, reason: str):
        super().__init__(f"Fact checking failed: {reason}", {"reason": reason})


class EvaluatorException(AgentException):
    error_code = "EVALUATOR_ERROR"

    def __init__(self, reason: str):
        super().__init__(f"Evaluation failed: {reason}", {"reason": reason})


class MemoryException(AgentException):
    error_code = "MEMORY_ERROR"

    def __init__(self, reason: str):
        super().__init__(f"Memory retrieval failed: {reason}", {"reason": reason})
