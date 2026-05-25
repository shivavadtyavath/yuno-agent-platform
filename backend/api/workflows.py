"""
Workflow CRUD + execution API endpoints.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.models.workflow import Workflow
from backend.models.execution import Execution
from backend.runtime.engine import engine as orchestration_engine
from backend.templates import ALL_TEMPLATES

router = APIRouter(prefix="/workflows", tags=["workflows"])


# ─── Pydantic Schemas ─────────────────────────────────────────────────────────

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""
    graph: Dict[str, Any] = Field(default_factory=dict)
    is_template: bool = False
    template_name: str = ""


class WorkflowUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    graph: Optional[Dict[str, Any]] = None
    is_active: Optional[bool] = None


class WorkflowResponse(BaseModel):
    id: str
    name: str
    description: str
    graph: Dict[str, Any]
    is_template: bool
    template_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class WorkflowRunRequest(BaseModel):
    message: str = Field(..., min_length=1)
    execution_id: Optional[str] = None


class WorkflowRunResponse(BaseModel):
    execution_id: str
    workflow_id: str
    response: str


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/", response_model=List[WorkflowResponse])
def list_workflows(db: Session = Depends(get_db)):
    return db.query(Workflow).order_by(Workflow.created_at.desc()).all()


@router.get("/templates", response_model=List[Dict])
def list_templates():
    """Return all pre-built workflow templates."""
    return [
        {
            "name": t["name"],
            "description": t["description"],
            "template_name": t["template_name"],
            "node_count": len(t["graph"].get("nodes", [])),
            "graph": t["graph"],
        }
        for t in ALL_TEMPLATES
    ]


@router.post("/from-template/{template_name}", response_model=WorkflowResponse, status_code=201)
def create_from_template(template_name: str, db: Session = Depends(get_db)):
    """Instantiate a workflow from a pre-built template."""
    template = next((t for t in ALL_TEMPLATES if t["template_name"] == template_name), None)
    if not template:
        raise HTTPException(status_code=404, detail=f"Template '{template_name}' not found")

    workflow = Workflow(
        id=str(uuid.uuid4()),
        name=template["name"],
        description=template["description"],
        graph=template["graph"],
        is_template=True,
        template_name=template_name,
    )
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.post("/", response_model=WorkflowResponse, status_code=status.HTTP_201_CREATED)
def create_workflow(payload: WorkflowCreate, db: Session = Depends(get_db)):
    workflow = Workflow(id=str(uuid.uuid4()), **payload.model_dump())
    db.add(workflow)
    db.commit()
    db.refresh(workflow)
    return workflow


@router.get("/{workflow_id}", response_model=WorkflowResponse)
def get_workflow(workflow_id: str, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return wf


@router.put("/{workflow_id}", response_model=WorkflowResponse)
def update_workflow(workflow_id: str, payload: WorkflowUpdate, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    for key, value in payload.model_dump(exclude_none=True).items():
        setattr(wf, key, value)
    wf.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(wf)
    return wf


@router.delete("/{workflow_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(workflow_id: str, db: Session = Depends(get_db)):
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    db.delete(wf)
    db.commit()


@router.post("/{workflow_id}/run", response_model=WorkflowRunResponse)
async def run_workflow(
    workflow_id: str,
    payload: WorkflowRunRequest,
    db: Session = Depends(get_db),
):
    """Execute a workflow with a given input message."""
    wf = db.query(Workflow).filter(Workflow.id == workflow_id).first()
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")

    if not wf.is_active:
        raise HTTPException(status_code=400, detail="Workflow is not active")

    execution_id = payload.execution_id or str(uuid.uuid4())

    exec_record = Execution(
        id=execution_id,
        workflow_id=workflow_id,
        trigger="api",
        status="running",
        input_text=payload.message,
    )
    db.add(exec_record)
    db.commit()

    try:
        workflow_config = {
            "id": wf.id,
            "name": wf.name,
            "graph": wf.graph,
        }
        response = await orchestration_engine.invoke_workflow(
            workflow_config=workflow_config,
            user_message=payload.message,
            execution_id=execution_id,
            db=db,
        )

        exec_record.status = "completed"
        exec_record.output_text = response
        exec_record.finished_at = datetime.now(timezone.utc)
        db.commit()

        return WorkflowRunResponse(
            execution_id=execution_id,
            workflow_id=workflow_id,
            response=response,
        )
    except Exception as e:
        exec_record.status = "failed"
        exec_record.error = str(e)
        exec_record.finished_at = datetime.now(timezone.utc)
        db.commit()
        raise HTTPException(status_code=500, detail=str(e))
