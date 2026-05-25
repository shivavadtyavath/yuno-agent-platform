"""
Execution history and message log API endpoints.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from datetime import datetime

from backend.core.database import get_db
from backend.models.execution import Execution, Message

router = APIRouter(prefix="/executions", tags=["executions"])


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    agent_id: Optional[str]
    agent_name: Optional[str]
    tool_name: Optional[str]
    tokens: int
    created_at: datetime

    model_config = {"from_attributes": True}


class ExecutionResponse(BaseModel):
    id: str
    workflow_id: Optional[str]
    agent_id: Optional[str]
    trigger: str
    status: str
    input_text: str
    output_text: str
    error: str
    total_tokens: int
    prompt_tokens: int
    completion_tokens: int
    estimated_cost_usd: str
    started_at: datetime
    finished_at: Optional[datetime]
    messages: List[MessageResponse] = []

    model_config = {"from_attributes": True}


@router.get("/", response_model=List[ExecutionResponse])
def list_executions(
    limit: int = Query(default=50, le=200),
    offset: int = Query(default=0),
    agent_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    db: Session = Depends(get_db),
):
    """List executions with optional filtering."""
    query = db.query(Execution)
    if agent_id:
        query = query.filter(Execution.agent_id == agent_id)
    if status:
        query = query.filter(Execution.status == status)
    return (
        query.order_by(Execution.started_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{execution_id}", response_model=ExecutionResponse)
def get_execution(execution_id: str, db: Session = Depends(get_db)):
    """Get a single execution with all its messages."""
    exec_record = db.query(Execution).filter(Execution.id == execution_id).first()
    if not exec_record:
        raise HTTPException(status_code=404, detail="Execution not found")
    return exec_record


@router.get("/{execution_id}/messages", response_model=List[MessageResponse])
def get_execution_messages(execution_id: str, db: Session = Depends(get_db)):
    """Get all messages for an execution."""
    exec_record = db.query(Execution).filter(Execution.id == execution_id).first()
    if not exec_record:
        raise HTTPException(status_code=404, detail="Execution not found")
    return exec_record.messages


@router.get("/stats/summary")
def get_stats(db: Session = Depends(get_db)):
    """Get platform-wide statistics."""
    from sqlalchemy import func
    from backend.models.agent import Agent
    from backend.models.workflow import Workflow

    total_agents = db.query(func.count(Agent.id)).scalar()
    total_workflows = db.query(func.count(Workflow.id)).scalar()
    total_executions = db.query(func.count(Execution.id)).scalar()
    total_tokens = db.query(func.sum(Execution.total_tokens)).scalar() or 0
    completed = db.query(func.count(Execution.id)).filter(Execution.status == "completed").scalar()
    failed = db.query(func.count(Execution.id)).filter(Execution.status == "failed").scalar()

    return {
        "total_agents": total_agents,
        "total_workflows": total_workflows,
        "total_executions": total_executions,
        "completed_executions": completed,
        "failed_executions": failed,
        "total_tokens_used": total_tokens,
        "success_rate": round(completed / total_executions * 100, 1) if total_executions else 0,
    }
