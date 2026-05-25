"""
Workflow ORM model — stores the graph definition as JSON.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, Boolean, DateTime, JSON

from backend.core.database import Base


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


class Workflow(Base):
    __tablename__ = "workflows"

    id = Column(String(36), primary_key=True, default=_uuid)
    name = Column(String(128), nullable=False)
    description = Column(Text, default="")

    # React Flow graph definition: {nodes: [...], edges: [...]}
    graph = Column(JSON, nullable=False, default=dict)

    # Template flag
    is_template = Column(Boolean, default=False)
    template_name = Column(String(64), default="")

    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), default=_now)
    updated_at = Column(DateTime(timezone=True), default=_now, onupdate=_now)
