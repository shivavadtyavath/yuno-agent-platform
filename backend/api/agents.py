"""
Agent CRUD API endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.agent import Agent
from backend.runtime.engine import engine as orchestration_engine
from backend.runtime.tools import list_available_tools

router = APIRouter(prefix="/agents", tags=["agents"])


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    role: str = Field(default="assistant", max_length=256)
    system_prompt: str = Field(default="You are a helpful assistant.")
    model: str = Field(default="gpt-4o-mini")
    tools: List[str] = Field(default_factory=list)
    channels: List[str] = Field(default_factory=list)
    memory_enabled: bool = True
    memory_window: str = "10"
    max_tokens_per_turn: str = "2000"
    max_turns: str = "20"
    temperature: str = "0.7"
    schedule: str = ""
    schedule_task: str = ""
    personality: Dict[str, Any] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    tools: Optional[List[str]] = None
    channels: Optional[List[str]] = None
    memory_enabled: Optional[bool] = None
    memory_window: Optional[str] = None
    max_tokens_per_turn: Optional[str] = None
    max_turns: Optional[str] = None
    temperature: Optional[str] = None
    schedule: Optional[str] = None
    schedule_task: Optional[str] = None
    personality: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class AgentResponse(BaseModel):
    id: str
    name: str
    role: str
    system_prompt: str
    model: str
    tools: List[str]
    channels: List[str]
    memory_enabled: bool
    memory_window: str
    max_tokens_per_turn: str
    max_turns: str
    temperature: str
    schedule: str
    schedule_task: str
    personality: Dict[str, Any]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class InvokeRequest(BaseModel):
    message: str = Field(..., min_length=1)
    execution_id: Optional[str] = None


class InvokeResponse(BaseModel):
    execution_id: str
    agent_id: str
    response: str


def _agent_to_dict(agent: Agent) -> Dict:
    return {
        "id": agent.id,
        "name": agent.name,
        "role": agent.role,
        "system_prompt": agent.system_prompt,
        "model": agent.model,
        "tools": agent.tools or [],
        "channels": agent.channels or [],
        "memory_enabled": agent.memory_enabled,
        "memory_window": agent.memory_window,
        "max_tokens_per_turn": agent.max_tokens_per_turn,
        "max_turns": agent.max_turns,
        "temperature": agent.temperature,
        "schedule": agent.schedule,
        "schedule_task": agent.schedule_task,
        "personality": agent.personality or {},
        "is_active": agent.is_active,
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[AgentResponse])
def list_agents(db: Session = Depends(get_db)):
    """List all agents."""
    return db.query(Agent).order_by(Agent.created_at.desc()).all()


@router.post("/", response_model=AgentResponse, status_code=status.HTTP_201_CREATED)
def create_agent(payload: AgentCreate, db: Session = Depends(get_db)):
    """Create a new agent."""
    agent = Agent(
        id=str(uuid.uuid4()),
        **payload.model_dump(),
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    # Register with the engine
    orchestration_engine.register_agent(_agent_to_dict(agent))

    return agent


@router.get("/tools", response_model=List[Dict])
def get_available_tools():
    """List all tools available for agents."""
    return list_available_tools()


@router.get("/{agent_id}", response_model=AgentResponse)
def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get a single agent by ID."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")
    return agent


@router.put("/{agent_id}", response_model=AgentResponse)
def update_agent(agent_id: str, payload: AgentUpdate, db: Session = Depends(get_db)):
    """Update an agent."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    update_data = payload.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(agent, key, value)

    agent.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(agent)

    # Re-register with engine
    orchestration_engine.register_agent(_agent_to_dict(agent))

    return agent


@router.delete("/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_agent(agent_id: str, db: Session = Depends(get_db)):
    """Delete an agent."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    orchestration_engine.unregister_agent(agent_id)
    db.delete(agent)
    db.commit()


@router.post("/{agent_id}/invoke", response_model=InvokeResponse)
async def invoke_agent(
    agent_id: str,
    payload: InvokeRequest,
    db: Session = Depends(get_db),
):
    """Directly invoke an agent with a message."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    if not agent.is_active:
        raise HTTPException(status_code=400, detail="Agent is not active")

    execution_id = payload.execution_id or str(uuid.uuid4())

    # Create execution record
    from backend.models.execution import Execution
    exec_record = Execution(
        id=execution_id,
        agent_id=agent_id,
        trigger="api",
        status="running",
        input_text=payload.message,
    )
    db.add(exec_record)
    db.commit()

    try:
        response = await orchestration_engine.invoke_agent(
            agent_id=agent_id,
            user_message=payload.message,
            execution_id=execution_id,
            db=db,
        )
        return InvokeResponse(
            execution_id=execution_id,
            agent_id=agent_id,
            response=response,
        )
    except Exception as e:
        exec_record.status = "failed"
        exec_record.error = str(e)
        exec_record.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{agent_id}/clear-memory", status_code=status.HTTP_200_OK)
def clear_agent_memory(agent_id: str, db: Session = Depends(get_db)):
    """Clear an agent's memory."""
    agent = db.query(Agent).filter(Agent.id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    from backend.runtime.memory import get_memory
    memory = get_memory(agent_id)
    memory.clear()
    return {"message": f"Memory cleared for agent {agent.name}"}
