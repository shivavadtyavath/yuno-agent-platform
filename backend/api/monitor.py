"""
Real-time monitoring WebSocket endpoint.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from backend.core.events import bus

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/monitor", tags=["monitor"])


@router.websocket("/ws")
async def websocket_monitor(websocket: WebSocket):
    """
    WebSocket endpoint for real-time event streaming.
    Clients connect here to receive live agent events.
    """
    await websocket.accept()
    bus.connect(websocket)
    logger.info("Monitor WebSocket connected")

    # Send recent history on connect
    history = bus.get_history(limit=50)
    for event in history:
        import json
        try:
            await websocket.send_text(json.dumps(event))
        except Exception:
            break

    try:
        while True:
            # Keep connection alive — client can send pings
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        logger.info("Monitor WebSocket disconnected")
    finally:
        bus.disconnect(websocket)


@router.get("/history")
def get_event_history(limit: int = 100):
    """Get recent event history (REST fallback for non-WS clients)."""
    return bus.get_history(limit=limit)
