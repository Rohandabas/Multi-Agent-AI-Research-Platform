"""
JobManager — manages in-memory job state and WebSocket connections.
Every active research job has a state dict and a set of connected WebSocket clients.
"""
from __future__ import annotations

import asyncio
import json
from typing import TYPE_CHECKING

from app.schemas.response import ProgressEvent

if TYPE_CHECKING:
    from fastapi import WebSocket


class JobManager:
    """
    Central hub for job state + WebSocket live progress broadcasting.

    One instance lives for the lifetime of the FastAPI app (app-level singleton).
    """

    def __init__(self):
        # job_id → list of connected WebSocket connections
        self._connections: dict[str, list["WebSocket"]] = {}
        # job_id → latest status dict
        self._job_states: dict[str, dict] = {}
        # job_id → asyncio.Event (set when job completes)
        self._completion_events: dict[str, asyncio.Event] = {}

    # ─── Job lifecycle ────────────────────────────────────────────────────────

    def create_job(self, job_id: str, report_id: str, query: str):
        """Initialize a new job's state."""
        self._job_states[job_id] = {
            "job_id": job_id,
            "report_id": report_id,
            "query": query,
            "status": "running",
            "progress": 0,
            "cost_so_far": 0.0,
            "current_agent": None,
            "events": [],
        }
        self._connections[job_id] = []
        self._completion_events[job_id] = asyncio.Event()

    def update_job(self, job_id: str, **kwargs):
        """Update job state fields."""
        if job_id in self._job_states:
            self._job_states[job_id].update(kwargs)

    def get_job(self, job_id: str) -> dict | None:
        return self._job_states.get(job_id)

    def complete_job(self, job_id: str):
        """Mark a job as complete and signal waiting clients."""
        if job_id in self._job_states:
            self._job_states[job_id]["status"] = "complete"
            self._job_states[job_id]["progress"] = 100
        if job_id in self._completion_events:
            self._completion_events[job_id].set()

    def fail_job(self, job_id: str, error: str):
        """Mark a job as failed."""
        if job_id in self._job_states:
            self._job_states[job_id]["status"] = "error"
            self._job_states[job_id]["error"] = error
        if job_id in self._completion_events:
            self._completion_events[job_id].set()

    # ─── WebSocket connections ────────────────────────────────────────────────

    async def connect(self, job_id: str, websocket: "WebSocket"):
        """Accept and register a WebSocket connection for a job."""
        await websocket.accept()
        if job_id not in self._connections:
            self._connections[job_id] = []
        self._connections[job_id].append(websocket)

        # Send current state to newly connected client
        state = self._job_states.get(job_id)
        if state:
            from datetime import datetime
            await self._send_to_ws(websocket, {
                "event": "connected",
                "message": "Connected to job progress stream",
                "timestamp": datetime.utcnow().isoformat(),
                "state": state,
            })

    def disconnect(self, job_id: str, websocket: "WebSocket"):
        """Remove a WebSocket connection."""
        if job_id in self._connections:
            try:
                self._connections[job_id].remove(websocket)
            except ValueError:
                pass

    async def broadcast(self, job_id: str, event: ProgressEvent):
        """Send a progress event to all connected clients for this job."""
        if job_id in self._job_states:
            # Update job state
            self._job_states[job_id]["progress"] = event.progress
            self._job_states[job_id]["cost_so_far"] = event.cost_so_far
            if event.agent:
                self._job_states[job_id]["current_agent"] = event.agent
            # Keep event history (last 100)
            events = self._job_states[job_id].setdefault("events", [])
            events.append(event.model_dump())
            if len(events) > 100:
                events.pop(0)

        payload = event.model_dump()
        disconnected = []

        for ws in self._connections.get(job_id, []):
            try:
                await self._send_to_ws(ws, payload)
            except Exception:
                disconnected.append(ws)

        # Clean up dead connections
        for ws in disconnected:
            self.disconnect(job_id, ws)

    async def broadcast_dict(self, job_id: str, payload: dict):
        """Broadcast a raw dict to all WebSocket clients."""
        for ws in self._connections.get(job_id, []):
            try:
                await self._send_to_ws(ws, payload)
            except Exception:
                pass

    async def _send_to_ws(self, ws: "WebSocket", data: dict):
        await ws.send_text(json.dumps(data, default=str))

    # ─── Cleanup ─────────────────────────────────────────────────────────────

    def cleanup_job(self, job_id: str):
        """Remove all state for a completed job."""
        self._connections.pop(job_id, None)
        self._job_states.pop(job_id, None)
        self._completion_events.pop(job_id, None)

    @property
    def active_jobs(self) -> list[str]:
        return list(self._job_states.keys())


# ─── App-level singleton ──────────────────────────────────────────────────────
job_manager = JobManager()
