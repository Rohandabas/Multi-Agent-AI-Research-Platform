"""
WebSocket endpoint — live progress streaming for research jobs.
"""
from __future__ import annotations

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.job_manager import job_manager

router = APIRouter(tags=["websocket"])


@router.websocket("/ws/{job_id}")
async def research_websocket(websocket: WebSocket, job_id: str):
    """
    WebSocket endpoint for live research progress.

    Connect: ws://localhost:8000/ws/{job_id}

    Events received:
      - connected: Initial connection with current state
      - agent_start: Agent started
      - agent_complete: Agent finished
      - agent_error: Agent failed
      - info: General info message
      - report_ready: Research complete, report available
    """
    await job_manager.connect(job_id, websocket)

    try:
        while True:
            # Keep connection alive — wait for client messages (e.g., ping)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"event": "pong"}')
    except WebSocketDisconnect:
        job_manager.disconnect(job_id, websocket)
    except Exception:
        job_manager.disconnect(job_id, websocket)
