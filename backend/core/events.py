"""
In-process WebSocket event bus.

Any part of the backend can call `emit(event)` and all connected
WebSocket clients will receive it in real time.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class Event:
    type: str                          # e.g. "agent_message", "tool_call", "log"
    payload: Dict[str, Any] = field(default_factory=dict)
    execution_id: Optional[str] = None
    agent_id: Optional[str] = None
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_json(self) -> str:
        return json.dumps(asdict(self))


class EventBus:
    """Singleton event bus — broadcast to all active WebSocket connections."""

    def __init__(self) -> None:
        self._connections: List[WebSocket] = []
        self._history: List[Event] = []          # last 500 events kept in memory
        self._max_history = 500

    def connect(self, ws: WebSocket) -> None:
        self._connections.append(ws)
        logger.debug("WS client connected. Total: %d", len(self._connections))

    def disconnect(self, ws: WebSocket) -> None:
        self._connections = [c for c in self._connections if c is not ws]
        logger.debug("WS client disconnected. Total: %d", len(self._connections))

    async def emit(self, event: Event) -> None:
        """Broadcast event to all connected clients."""
        self._history.append(event)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history :]

        dead: List[WebSocket] = []
        for ws in list(self._connections):
            try:
                await ws.send_text(event.to_json())
            except Exception:
                dead.append(ws)

        for ws in dead:
            self.disconnect(ws)

    def emit_sync(self, event: Event) -> None:
        """Fire-and-forget from synchronous code (spawns a task if loop running)."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.emit(event))
            else:
                loop.run_until_complete(self.emit(event))
        except RuntimeError:
            pass  # no event loop — skip (e.g. during tests)

    def get_history(self, limit: int = 100) -> List[Dict]:
        return [asdict(e) for e in self._history[-limit:]]


# Global singleton
bus = EventBus()
