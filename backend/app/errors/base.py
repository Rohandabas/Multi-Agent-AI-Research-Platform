"""
Base exception for the entire research platform.
All exceptions inherit from ResearchException.
"""
from typing import Optional


class ResearchException(Exception):
    """Base exception for the Multi-Agent Research Platform."""

    def __init__(self, message: str, details: Optional[dict] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

    def to_dict(self) -> dict:
        return {
            "error": self.__class__.__name__,
            "message": self.message,
            "details": self.details,
        }
