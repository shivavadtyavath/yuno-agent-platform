"""
Telegram Bot Channel Integration.

Bridges Telegram users ↔ Agent runtime.
- /start — welcome message
- /agents — list available agents
- /use <agent_name> — select an agent to chat with
- Any text message — routed to the selected agent
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Dict, Optional

from backend.core.config import settings
from backend.core.events import bus, Event

logger = logging.getLogger(__name__)

try:
    from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
    from telegram.ext import (
        Application, CommandHandler, MessageHandler,
        CallbackQueryHandler, ContextTypes, filters
    )
    _TELEGRAM_AVAILABLE = True
except ImportError:
    _TELEGRAM_AVAILABLE = False
    logger.warning("python-telegram-bot not installed — Telegram channel disabled.")


# Per-chat state: which agent is selected
_chat_agent_map: Dict[int, str] = {}   # chat_id → agent_id
_chat_exec_map: Dict[int, str] = {}    # chat_id → execution_id (for conversation continuity)

# Will be injected at startup
_engine_ref = None
_db_factory = None


def init_telegram(engine, db_factory) -> None:
    global _engine_ref, _db_factory
    _engine_ref = engine
    _db_factory = db_factory


async def _start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "👋 Welcome to *Yuno AI Agent Platform*!\n\n"
        "I can connect you with AI agents. Use:\n"
        "• /agents — see available agents\n"
        "• /use <agent\\_name> — select an agent\n"
        "• Then just type your message!\n\n"
        "_Powered by LangGraph + Yuno_",
        parse_mode="Markdown",
    )


async def _list_agents(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if _engine_ref is None:
        await update.message.reply_text("⚠️ Engine not initialized.")
        return

    agents = list(_engine_ref._configs.values())
    if not agents:
        await update.message.reply_text("No agents registered yet. Create one in the web UI!")
        return

    # Build inline keyboard
    keyboard = []
    for agent in agents:
        if agent.get("is_active", True):
            keyboard.append([
                InlineKeyboardButton(
                    f"🤖 {agent['name']} — {agent.get('role', '')}",
                    callback_data=f"select_agent:{agent['id']}",
                )
            ])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Select an agent to chat with:",
        reply_markup=reply_markup,
    )


async def _select_agent_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("select_agent:"):
        agent_id = data.split(":", 1)[1]
        chat_id = query.message.chat_id

        if _engine_ref and agent_id in _engine_ref._configs:
            agent = _engine_ref._configs[agent_id]
            _chat_agent_map[chat_id] = agent_id
            _chat_exec_map[chat_id] = str(uuid.uuid4())  # new conversation

            await query.edit_message_text(
                f"✅ Connected to *{agent['name']}*\n"
                f"_{agent.get('role', 'AI Assistant')}_\n\n"
                f"Start chatting! Type your message below.",
                parse_mode="Markdown",
            )
        else:
            await query.edit_message_text("❌ Agent not found.")


async def _use_agent(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Select agent by name: /use Research Agent"""
    if not context.args:
        await update.message.reply_text("Usage: /use <agent name>")
        return

    agent_name = " ".join(context.args)
    chat_id = update.message.chat_id

    if _engine_ref is None:
        await update.message.reply_text("⚠️ Engine not initialized.")
        return

    for agent_id, agent in _engine_ref._configs.items():
        if agent["name"].lower() == agent_name.lower():
            _chat_agent_map[chat_id] = agent_id
            _chat_exec_map[chat_id] = str(uuid.uuid4())
            await update.message.reply_text(
                f"✅ Switched to *{agent['name']}*\nStart chatting!",
                parse_mode="Markdown",
            )
            return

    await update.message.reply_text(f"❌ No agent named '{agent_name}'. Use /agents to see available agents.")


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    user_text = update.message.text

    if _engine_ref is None:
        await update.message.reply_text("⚠️ Engine not initialized.")
        return

    agent_id = _chat_agent_map.get(chat_id)
    if not agent_id:
        await update.message.reply_text(
            "Please select an agent first with /agents or /use <agent name>"
        )
        return

    agent = _engine_ref._configs.get(agent_id)
    if not agent:
        await update.message.reply_text("❌ Selected agent no longer exists. Use /agents to pick another.")
        _chat_agent_map.pop(chat_id, None)
        return

    # Show typing indicator
    await context.bot.send_chat_action(chat_id=chat_id, action="typing")

    execution_id = _chat_exec_map.get(chat_id, str(uuid.uuid4()))

    # Emit event
    await bus.emit(Event(
        type="telegram_message",
        execution_id=execution_id,
        agent_id=agent_id,
        payload={
            "chat_id": chat_id,
            "user_message": user_text,
            "agent_name": agent["name"],
        },
    ))

    try:
        # Get DB session
        db = None
        if _db_factory:
            db = next(_db_factory())

        response = await _engine_ref.invoke_agent(
            agent_id=agent_id,
            user_message=user_text,
            execution_id=execution_id,
            db=db,
        )

        if db:
            db.close()

        # Telegram has 4096 char limit
        if len(response) > 4000:
            chunks = [response[i:i+4000] for i in range(0, len(response), 4000)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        else:
            await update.message.reply_text(response)

    except Exception as e:
        logger.error("Telegram message handling failed: %s", e)
        await update.message.reply_text(
            f"⚠️ Sorry, I encountered an error: {str(e)[:200]}"
        )


async def _status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    agent_id = _chat_agent_map.get(chat_id)

    if agent_id and _engine_ref and agent_id in _engine_ref._configs:
        agent = _engine_ref._configs[agent_id]
        await update.message.reply_text(
            f"📊 *Current Status*\n"
            f"Agent: {agent['name']}\n"
            f"Role: {agent.get('role', 'N/A')}\n"
            f"Model: {agent.get('model', 'N/A')}\n"
            f"Tools: {', '.join(agent.get('tools', [])) or 'None'}",
            parse_mode="Markdown",
        )
    else:
        await update.message.reply_text("No agent selected. Use /agents to pick one.")


def create_telegram_app() -> Optional[object]:
    """Create and configure the Telegram bot application."""
    if not _TELEGRAM_AVAILABLE:
        return None

    token = settings.telegram_bot_token
    if not token or token == "your_telegram_bot_token_here":
        logger.warning("Telegram bot token not configured — bot disabled.")
        return None

    app = Application.builder().token(token).build()

    app.add_handler(CommandHandler("start", _start))
    app.add_handler(CommandHandler("agents", _list_agents))
    app.add_handler(CommandHandler("use", _use_agent))
    app.add_handler(CommandHandler("status", _status))
    app.add_handler(CallbackQueryHandler(_select_agent_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message))

    return app


async def run_telegram_bot(app) -> None:
    """Run the Telegram bot (polling mode — no webhook needed for local dev)."""
    if app is None:
        return
    logger.info("Starting Telegram bot...")
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    logger.info("Telegram bot is running.")
