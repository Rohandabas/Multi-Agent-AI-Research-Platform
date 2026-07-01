"""
AgentLogger — structured per-agent logging with duration, tokens, cost tracking.
Every agent logs: started, info, warning, error, retry, finished.
"""
import logging
import time
import sys
from dataclasses import dataclass, field
from typing import Optional
from datetime import datetime

from app.config.settings import settings


# ─── Configure root logger ────────────────────────────────────────────────────
def setup_logging():
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)
    fmt = "%(asctime)s | %(levelname)-8s | %(name)-25s | %(message)s"
    datefmt = "%H:%M:%S"

    logging.basicConfig(
        level=level,
        format=fmt,
        datefmt=datefmt,
        handlers=[
            logging.StreamHandler(sys.stdout),
        ],
    )

    # Silence noisy third-party loggers
    for name in ["httpx", "chromadb", "urllib3", "httpcore"]:
        logging.getLogger(name).setLevel(logging.WARNING)


# ─── Agent log dataclass ───────────────────────────────────────────────────────
@dataclass
class AgentLog:
    agent: str
    job_id: str
    started_at: float = field(default_factory=time.time)
    finished_at: Optional[float] = None
    tokens_input: int = 0
    tokens_output: int = 0
    cost_usd: float = 0.0
    retries: int = 0
    error: Optional[str] = None
    messages: list = field(default_factory=list)

    @property
    def duration(self) -> float:
        end = self.finished_at or time.time()
        return round(end - self.started_at, 2)

    @property
    def total_tokens(self) -> int:
        return self.tokens_input + self.tokens_output

    def to_dict(self) -> dict:
        return {
            "agent": self.agent,
            "job_id": self.job_id,
            "duration_seconds": self.duration,
            "tokens_input": self.tokens_input,
            "tokens_output": self.tokens_output,
            "total_tokens": self.total_tokens,
            "cost_usd": round(self.cost_usd, 6),
            "retries": self.retries,
            "error": self.error,
            "finished_at": datetime.utcfromtimestamp(
                self.finished_at or time.time()
            ).isoformat(),
        }


# ─── AgentLogger ─────────────────────────────────────────────────────────────
class AgentLogger:
    """
    Structured logger for a single agent run.

    Usage:
        log = AgentLogger("SearchAgent", job_id="abc123")
        log.started()
        log.info("Querying Tavily...")
        log.finished(tokens_input=500, tokens_output=200, cost_usd=0.005)
    """

    def __init__(self, agent_name: str, job_id: str = ""):
        self.agent_name = agent_name
        self.job_id = job_id
        self._log = AgentLog(agent=agent_name, job_id=job_id)
        self._logger = logging.getLogger(agent_name)

    def started(self, message: str = ""):
        self._log.started_at = time.time()
        suffix = f" — {message}" if message else ""
        self._logger.info(f"STARTED  job={self.job_id}{suffix}")

    def info(self, message: str):
        self._log.messages.append(message)
        self._logger.info(message)

    def warning(self, message: str):
        self._logger.warning(message)

    def error(self, message: str, exc: Optional[Exception] = None):
        self._log.error = message
        self._logger.error(message, exc_info=exc if exc else False)

    def retry(self, attempt: int, reason: str):
        self._log.retries = attempt
        self._logger.warning(f"RETRY    attempt={attempt} reason={reason}")

    def finished(
        self,
        tokens_input: int = 0,
        tokens_output: int = 0,
        cost_usd: float = 0.0,
    ):
        self._log.finished_at = time.time()
        self._log.tokens_input = tokens_input
        self._log.tokens_output = tokens_output
        self._log.cost_usd = cost_usd

        self._logger.info(
            f"FINISHED "
            f"duration={self._log.duration}s  "
            f"tokens_in={tokens_input}  "
            f"tokens_out={tokens_output}  "
            f"cost=${cost_usd:.6f}"
        )

    def get_log(self) -> AgentLog:
        return self._log
