"""
Agent ORM model + Pydantic schemas.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Agent(Base):
    __tablename__ = "agents"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(128), nullable=False)
    role = Column(String(256), nullable=False, default="assistant")
    system_prompt = Column(Text, nullable=False, default="You are a helpful assistant.")
    model = Column(String(128), nullable=False, default="gpt-4o-mini")

    # Tools: list of tool names the agent is allowed to use
    tools = Column(JSON, nullable=False, default=list)

    # Channels: e.g. ["telegram"]
    channels = Column(JSON, nullable=False, default=list)

    # Memory config
    memory_enabled = Column(Boolean, default=True)
    memory_window = Column(String(16), default="10")  # last N messages

    # Guardrails / limits
    max_tokens_per_turn = Column(String(16), default="2000")
    max_turns = Column(String(16), default="20")
    temperature = Column(String(8), default="0.7")

    # Schedule (cron expression or empty)
    schedule = Column(String(64), default="")
    schedule_task = Column(Text, default="")  # what to do when scheduled

    # Personality / skills (free-form JSON)
    personality = Column(JSON, nullable=False, default=dict)

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)

    # Relationships
    executions = relationship("Execution", back_populates="agent", cascade="all, delete-orphan")
