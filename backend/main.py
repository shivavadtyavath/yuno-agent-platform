"""
Yuno AI Agent Orchestration Platform — FastAPI Backend
"""
from __future__ import annotations

import asyncio
import logging
import os
import sys

# Ensure the project root is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.core.config import settings
from backend.core.database import init_db, SessionLocal
from backend.runtime.engine import engine as orchestration_engine
from backend.runtime.tools.agent_messenger import set_engine

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator:
    """Startup and shutdown lifecycle."""
    logger.info("🚀 Starting Yuno AI Agent Platform...")

    # 1. Initialize database
    init_db()
    logger.info("✅ Database initialized")

    # 1.5. Seed default template agents if DB is empty
    db = SessionLocal()
    try:
        from backend.models.agent import Agent
        import uuid
        existing_agents = db.query(Agent).count()
        if existing_agents == 0:
            seeded_agents = [
                {
                    "name": "Triage Agent",
                    "role": "Customer Support Triage Specialist",
                    "system_prompt": (
                        "You are a customer support triage specialist. "
                        "When a customer message arrives, classify it as one of: "
                        "'billing', 'technical', 'general', or 'urgent'. "
                        "Then use send_message_to_agent to route it to the appropriate agent: "
                        "- For 'billing' or 'urgent': send to 'Escalation Agent' "
                        "- For 'technical' or 'general': send to 'Support Agent' "
                        "Summarize the customer's issue clearly when routing."
                    ),
                    "tools": ["send_message_to_agent", "get_current_datetime"],
                    "model": "gpt-4o-mini",
                },
                {
                    "name": "Support Agent",
                    "role": "Technical Support Specialist",
                    "system_prompt": (
                        "You are a friendly and knowledgeable technical support specialist. "
                        "Provide clear, step-by-step solutions to customer issues. "
                        "Use web_search if you need to look up specific technical information. "
                        "Always end with: 'Is there anything else I can help you with?'"
                    ),
                    "tools": ["web_search", "get_current_datetime"],
                    "model": "gpt-4o-mini",
                },
                {
                    "name": "Escalation Agent",
                    "role": "Senior Support & Billing Specialist",
                    "system_prompt": (
                        "You are a senior support specialist handling billing and urgent issues. "
                        "Be empathetic, professional, and solution-focused. "
                        "For billing issues, explain policies clearly and offer concrete resolutions. "
                        "For urgent issues, acknowledge the urgency and provide immediate next steps. "
                        "Always provide a case reference number (generate a random 6-digit number)."
                    ),
                    "tools": ["calculator", "get_current_datetime"],
                    "model": "gpt-4o-mini",
                },
                {
                    "name": "Research Agent",
                    "role": "Research Specialist",
                    "system_prompt": (
                        "You are a thorough research specialist. "
                        "When given a topic, use web_search to gather comprehensive information "
                        "from multiple angles. Search at least 3 different aspects of the topic. "
                        "Compile all findings into a structured research brief with sources. "
                        "Then pass your research to the Analyst Agent using send_message_to_agent."
                    ),
                    "tools": ["web_search", "get_current_datetime", "send_message_to_agent"],
                    "model": "gpt-4o-mini",
                },
                {
                    "name": "Analyst Agent",
                    "role": "Data & Insights Analyst",
                    "system_prompt": (
                        "You are an expert analyst. "
                        "When you receive research findings, analyze them critically: "
                        "- Identify the 3-5 most important insights "
                        "- Note any contradictions or gaps in the research "
                        "- Assess confidence levels for key claims "
                        "- Highlight actionable takeaways "
                        "Then send your analysis to the Writer Agent using send_message_to_agent."
                    ),
                    "tools": ["calculator", "send_message_to_agent"],
                    "model": "gpt-4o-mini",
                },
                {
                    "name": "Writer Agent",
                    "role": "Content Writer & Editor",
                    "system_prompt": (
                        "You are a skilled content writer. "
                        "When you receive an analysis, transform it into a polished, "
                        "well-structured report with: "
                        "- An executive summary (2-3 sentences) "
                        "- Key findings (bullet points) "
                        "- Detailed analysis (paragraphs) "
                        "- Conclusion and recommendations "
                        "Write in a clear, professional tone suitable for business stakeholders."
                    ),
                    "tools": [],
                    "model": "gpt-4o-mini",
                }
            ]
            for sa in seeded_agents:
                agent = Agent(
                    id=str(uuid.uuid4()),
                    name=sa["name"],
                    role=sa["role"],
                    system_prompt=sa["system_prompt"],
                    model=sa["model"],
                    tools=sa["tools"],
                    channels=[],
                    memory_enabled=True,
                    memory_window="10",
                    max_tokens_per_turn="2000",
                    max_turns="20",
                    temperature="0.7",
                    personality={},
                    is_active=True,
                )
                db.add(agent)
            db.commit()
            logger.info("✅ Seeded %d default agents", len(seeded_agents))
    except Exception as e:
        logger.error("Failed to seed default agents: %s", e)
        db.rollback()
    finally:
        db.close()

    # 2. Load all agents from DB into the engine
    db = SessionLocal()
    try:
        from backend.models.agent import Agent
        agents = db.query(Agent).filter(Agent.is_active == True).all()
        for agent in agents:
            orchestration_engine.register_agent({
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
                "temperature": agent.temperature,
                "personality": agent.personality or {},
                "is_active": agent.is_active,
            })
        logger.info("✅ Loaded %d agents into engine", len(agents))
    finally:
        db.close()

    # 3. Wire agent messenger tool to engine
    set_engine(orchestration_engine)
    logger.info("✅ Agent messenger tool wired")

    # 4. Start Telegram bot (if configured)
    telegram_task = None
    try:
        from backend.channels.telegram_bot import (
            create_telegram_app, run_telegram_bot, init_telegram
        )
        init_telegram(orchestration_engine, SessionLocal)
        tg_app = create_telegram_app()
        if tg_app:
            telegram_task = asyncio.create_task(run_telegram_bot(tg_app))
            logger.info("✅ Telegram bot started")
        else:
            logger.info("ℹ️  Telegram bot not configured (set TELEGRAM_BOT_TOKEN in .env)")
    except Exception as e:
        logger.warning("Telegram bot failed to start: %s", e)

    # 5. Seed workflow templates if DB is empty
    db = SessionLocal()
    try:
        from backend.models.workflow import Workflow
        from backend.templates import ALL_TEMPLATES
        import uuid

        existing = db.query(Workflow).filter(Workflow.is_template == True).count()
        if existing == 0:
            for tmpl in ALL_TEMPLATES:
                wf = Workflow(
                    id=str(uuid.uuid4()),
                    name=tmpl["name"],
                    description=tmpl["description"],
                    graph=tmpl["graph"],
                    is_template=True,
                    template_name=tmpl["template_name"],
                )
                db.add(wf)
            db.commit()
            logger.info("✅ Seeded %d workflow templates", len(ALL_TEMPLATES))
    finally:
        db.close()

    logger.info("🎉 Platform ready! API at http://localhost:8000")
    logger.info("📖 Docs at http://localhost:8000/docs")

    yield  # ← app is running

    # Shutdown
    logger.info("Shutting down...")
    if telegram_task:
        telegram_task.cancel()
        try:
            await telegram_task
        except asyncio.CancelledError:
            pass


# ─── App ─────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Yuno AI Agent Orchestration Platform",
    description=(
        "Build, configure, and orchestrate AI agents into collaborative workflows. "
        "Powered by LangGraph."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ─────────────────────────────────────────────────────────────────

from backend.api.agents import router as agents_router
from backend.api.workflows import router as workflows_router
from backend.api.executions import router as executions_router
from backend.api.monitor import router as monitor_router

app.include_router(agents_router, prefix="/api/v1")
app.include_router(workflows_router, prefix="/api/v1")
app.include_router(executions_router, prefix="/api/v1")
app.include_router(monitor_router, prefix="/api/v1")


# ─── Health check ─────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    return {
        "status": "ok",
        "platform": "Yuno AI Agent Orchestration Platform",
        "version": "1.0.0",
        "agents_loaded": len(orchestration_engine._configs),
    }


@app.get("/")
def root():
    return JSONResponse({
        "message": "Yuno AI Agent Orchestration Platform",
        "docs": "/docs",
        "health": "/health",
        "api": "/api/v1",
    })
