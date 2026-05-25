"""
Execution + Message ORM models.
Tracks every workflow run and every message exchanged.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Integer, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from backend.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Execution(Base):
    """One run of a workflow or a direct agent invocation."""
    __tablename__ = "executions"

    id = Column(String(36), primary_key=True, default=_uuid)
    workflow_id = Column(String(36), nullable=True)   # null = direct agent call
    agent_id = Column(String(36), ForeignKey("agents.id"), nullable=True)
    trigger = Column(String(32), default="manual")    # manual | schedule | telegram | slack
    status = Column(String(16), default="pending")    # pending | running | completed | failed
    input_text = Column(Text, default="")
    output_text = Column(Text, default="")
    error = Column(Text, default="")

    # Token / cost tracking
    total_tokens = Column(Integer, default=0)
    prompt_tokens = Column(Integer, default=0)
    completion_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(String(16), default="0.0000")

    started_at = Column(DateTime(timezone=True), default=_now)
    finished_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agent = relationship("Agent", back_populates="executions")
    messages = relationship("Message", back_populates="execution", cascade="all, delete-orphan",
                            order_by="Message.created_at")


class Message(Base):
    """Individual message within an execution (human, agent, tool, system)."""
    __tablename__ = "messages"

    id = Column(String(36), primary_key=True, default=_uuid)
    execution_id = Column(String(36), ForeignKey("executions.id"), nullable=False)
    role = Column(String(16), nullable=False)          # human | agent | tool | system
    content = Column(Text, nullable=False)
    agent_id = Column(String(36), nullable=True)       # which agent produced this
    agent_name = Column(String(128), nullable=True)
    tool_name = Column(String(64), nullable=True)      # set when role == "tool"
    tokens = Column(Integer, default=0)
    metadata_ = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=_now)

    execution = relationship("Execution", back_populates="messages")
