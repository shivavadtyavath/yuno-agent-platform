"""
LangGraph 1.x Agent Orchestration Engine.

Uses LangGraph's StateGraph with MessagesState.
Each agent runs a ReAct loop: LLM → (tool calls?) → tools → LLM → ...
Agent-to-agent communication is handled via the send_message_to_agent tool.
"""
from __future__ import annotations

import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Annotated, Dict, List, Optional, Sequence
import operator

from langchain_core.messages import (
    AIMessage, HumanMessage, SystemMessage, ToolMessage, BaseMessage
)
from langchain_core.tools import BaseTool
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from typing import TypedDict

from backend.core.config import settings
from backend.core.events import bus, Event
from backend.runtime.memory import get_memory
from backend.runtime.tools import get_tools

logger = logging.getLogger(__name__)


# ─── State definition ────────────────────────────────────────────────────────

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], operator.add]
    agent_id: str
    agent_name: str
    execution_id: str
    token_count: int
    iteration: int


# ─── Cost estimation ─────────────────────────────────────────────────────────

COST_PER_1K: Dict[str, Dict[str, float]] = {
    "gpt-4o-mini":    {"prompt": 0.000150, "completion": 0.000600},
    "gpt-4o":         {"prompt": 0.005000, "completion": 0.015000},
    "gpt-3.5-turbo":  {"prompt": 0.000500, "completion": 0.001500},
}

def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = COST_PER_1K.get(model, {"prompt": 0.001, "completion": 0.002})
    return (prompt_tokens / 1000 * rates["prompt"]) + (completion_tokens / 1000 * rates["completion"])


# ─── Tool executor (replaces ToolNode) ───────────────────────────────────────

async def execute_tools(
    last_message: AIMessage,
    tools_by_name: Dict[str, BaseTool],
    execution_id: str,
    agent_id: str,
    agent_name: str,
) -> List[ToolMessage]:
    """Execute all tool calls in an AIMessage and return ToolMessages."""
    results: List[ToolMessage] = []

    for tc in last_message.tool_calls:
        tool_name = tc["name"]
        tool_args = tc.get("args", {})
        tool_call_id = tc.get("id", str(uuid.uuid4()))

        # Emit tool_call event
        await bus.emit(Event(
            type="tool_call",
            execution_id=execution_id,
            agent_id=agent_id,
            payload={
                "agent_name": agent_name,
                "tool_name": tool_name,
                "args": tool_args,
            },
        ))

        tool = tools_by_name.get(tool_name)
        if tool is None:
            result_content = f"Error: tool '{tool_name}' not found."
        else:
            try:
                # Run sync tools in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                result_content = await loop.run_in_executor(
                    None, lambda: tool.invoke(tool_args)
                )
                result_content = str(result_content)
            except Exception as e:
                result_content = f"Tool error: {str(e)}"

        # Emit tool_result event
        await bus.emit(Event(
            type="tool_result",
            execution_id=execution_id,
            agent_id=agent_id,
            payload={
                "agent_name": agent_name,
                "tool_name": tool_name,
                "content": result_content[:500],
            },
        ))

        results.append(ToolMessage(
            content=result_content,
            tool_call_id=tool_call_id,
            name=tool_name,
        ))

    return results


class MockChatOpenAI:
    """
    Mock LLM execution engine to support fully functional, free student evaluation
    without requiring paid OpenAI API keys. Supports thinking animations, tool calls,
    multi-agent routing, and dynamic data calculation.
    """
    def __init__(self, model: str, api_key: str, base_url: str, agent_name: str, agent_role: str):
        self.model = model
        self.api_key = api_key
        self.base_url = base_url
        self.agent_name = agent_name
        self.agent_role = agent_role
        self.tools = []

    def bind_tools(self, tools):
        self.tools = tools
        return self

    async def ainvoke(self, context: List[BaseMessage]) -> AIMessage:
        # Simulate reasoning delay so user sees "Thinking..." state
        await asyncio.sleep(1.2)
        
        last_user_msg = ""
        for m in reversed(context):
            if isinstance(m, HumanMessage):
                last_user_msg = str(m.content)
                break
                
        # Gather all tool messages
        tool_msgs = [m for m in context if isinstance(m, ToolMessage)]
        
        import random
        
        # 1. Triage Agent Mock Logic
        if self.agent_name == "Triage Agent":
            if not tool_msgs:
                # Classify
                msg_lower = last_user_msg.lower()
                target = "Support Agent"
                if any(x in msg_lower for x in ["bill", "price", "charge", "refund", "pay", "urgent", "escalat"]):
                    target = "Escalation Agent"
                
                tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
                return AIMessage(
                    content=f"Classified query as billing/urgent or technical. Routing to {target}.",
                    tool_calls=[{
                        "name": "send_message_to_agent",
                        "args": {"agent_name": target, "message": last_user_msg},
                        "id": tool_call_id
                    }]
                )
            else:
                last_res = tool_msgs[-1].content
                return AIMessage(
                    content=f"Hello! I am the Triage Agent. I have routed your request to the specialist agent. Here is their response:\n\n{last_res}"
                )

        # 2. Support Agent Mock Logic
        elif self.agent_name == "Support Agent":
            if not tool_msgs and any(t.name == "web_search" for t in self.tools):
                tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
                return AIMessage(
                    content="Searching technical documents for a solution...",
                    tool_calls=[{
                        "name": "web_search",
                        "args": {"query": last_user_msg},
                        "id": tool_call_id
                    }]
                )
            else:
                search_res = tool_msgs[-1].content if tool_msgs else "No active technical notes."
                return AIMessage(
                    content=(
                        f"Hello! I am the Support Agent. I investigated your query:\n\n"
                        f"**Search Insights:** {search_res[:150]}...\n\n"
                        f"Here is the solution:\n"
                        f"1. Check your settings and configuration file.\n"
                        f"2. Verify network ports and environmental configurations.\n"
                        f"3. Clear local cache and restart the application.\n\n"
                        f"Is there anything else I can help you with?"
                    )
                )

        # 3. Escalation Agent Mock Logic
        elif self.agent_name == "Escalation Agent":
            if not tool_msgs and any(t.name == "calculator" for t in self.tools):
                tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
                return AIMessage(
                    content="Calculating priority index...",
                    tool_calls=[{
                        "name": "calculator",
                        "args": {"expression": "99 * 1.15"},
                        "id": tool_call_id
                    }]
                )
            else:
                calc_res = tool_msgs[-1].content if tool_msgs else "113.85"
                case_id = random.randint(100000, 999999)
                return AIMessage(
                    content=(
                        f"Hello! I am the Escalation Agent. I've received your escalation.\n\n"
                        f"I've calculated your account priority index based on billing metrics to be: {calc_res}.\n"
                        f"I've registered your ticket successfully.\n"
                        f"🎫 **Case Reference ID:** #{case_id}\n\n"
                        f"A senior representative has been assigned and will address this shortly."
                    )
                )

        # 4. Research Agent Mock Logic
        elif self.agent_name == "Research Agent":
            if not tool_msgs:
                tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
                return AIMessage(
                    content="Conducting broad search on the topic...",
                    tool_calls=[{
                        "name": "web_search",
                        "args": {"query": last_user_msg},
                        "id": tool_call_id
                    }]
                )
            elif len(tool_msgs) == 1:
                search_res = tool_msgs[0].content
                tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
                return AIMessage(
                    content="Passing research brief to the Analyst Agent...",
                    tool_calls=[{
                        "name": "send_message_to_agent",
                        "args": {"agent_name": "Analyst Agent", "message": f"Please analyze this research: {search_res}"},
                        "id": tool_call_id
                    }]
                )
            else:
                analyst_res = tool_msgs[-1].content
                return AIMessage(
                    content=f"Hello! I am the Research Agent. We have completed the research pipeline. Here is the final compiled output:\n\n{analyst_res}"
                )

        # 5. Analyst Agent Mock Logic
        elif self.agent_name == "Analyst Agent":
            if not tool_msgs:
                tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
                return AIMessage(
                    content="Analyzing datasets...",
                    tool_calls=[{
                        "name": "calculator",
                        "args": {"expression": "25 * 4"},
                        "id": tool_call_id
                    }]
                )
            elif len(tool_msgs) == 1:
                tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
                return AIMessage(
                    content="Routing analysis to Writer Agent...",
                    tool_calls=[{
                        "name": "send_message_to_agent",
                        "args": {"agent_name": "Writer Agent", "message": f"Please write a report. Base Context: {last_user_msg}"},
                        "id": tool_call_id
                    }]
                )
            else:
                writer_res = tool_msgs[-1].content
                return AIMessage(content=writer_res)

        # 6. Writer Agent Mock Logic
        elif self.agent_name == "Writer Agent":
            return AIMessage(
                content=(
                    f"# Executive Report: {last_user_msg[:40]}...\n\n"
                    f"### Executive Summary\n"
                    f"This report outlines structured findings gathered from automated research agents.\n\n"
                    f"### Key Analytical Insights\n"
                    f"- 📈 **Market Growth**: Significant demand increase identified.\n"
                    f"- ⚙️ **Process Efficiency**: Local operations are fully optimized.\n"
                    f"- 🛡️ **Risk Assessment**: Calculated safety thresholds remain robust.\n\n"
                    f"### Conclusion\n"
                    f"All metrics indicate a highly positive forecast. We recommend moving forward with integration."
                )
            )

        # Generic Custom Agent Mock Logic
        else:
            if not tool_msgs and self.tools:
                first_tool = self.tools[0]
                tool_call_id = f"call_{uuid.uuid4().hex[:8]}"
                args = {"query": last_user_msg} if first_tool.name == "web_search" else {"expression": "2 + 2"}
                return AIMessage(
                    content=f"Using tool '{first_tool.name}' to gather data...",
                    tool_calls=[{
                        "name": first_tool.name,
                        "args": args,
                        "id": tool_call_id
                    }]
                )
            else:
                res_part = f"\nTool Output: {tool_msgs[-1].content}" if tool_msgs else ""
                return AIMessage(
                    content=(
                        f"👋 Hello! I am **{self.agent_name}** ({self.agent_role}).\n"
                        f"I processed your query: '{last_user_msg}' using a completely free student-tier simulation runtime! {res_part}"
                    )
                )


# ─── Single-agent graph builder ───────────────────────────────────────────────

def build_agent_graph(agent_config: Dict[str, Any]):
    """
    Build a compiled LangGraph for a single agent.
    Uses LangGraph 1.x StateGraph API.
    """
    agent_id    = agent_config["id"]
    agent_name  = agent_config["name"]
    model_name  = agent_config.get("model", settings.default_model)
    system_prompt = agent_config.get("system_prompt", "You are a helpful assistant.")
    tool_names  = agent_config.get("tools", [])
    max_tokens  = int(agent_config.get("max_tokens_per_turn", 2000))
    temperature = float(agent_config.get("temperature", 0.7))
    memory_enabled = agent_config.get("memory_enabled", True)
    window_size = int(agent_config.get("memory_window", 10))
    max_iter    = int(agent_config.get("max_turns", 20))

    tools = get_tools(tool_names)
    tools_by_name: Dict[str, BaseTool] = {t.name: t for t in tools}

    role_name = agent_config.get("role", "assistant")
    if not settings.openai_api_key or "your_openai" in settings.openai_api_key or "sk-placeholder" in settings.openai_api_key:
        llm = MockChatOpenAI(
            model=model_name,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
            agent_name=agent_name,
            agent_role=role_name
        )
    else:
        llm = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    llm_with_tools = llm.bind_tools(tools) if tools else llm

    # ── Agent node ────────────────────────────────────────────────────────────
    async def agent_node(state: AgentState) -> Dict:
        messages   = state["messages"]
        exec_id    = state["execution_id"]
        iteration  = state["iteration"]

        if iteration >= max_iter:
            # Safety: force stop
            return {
                "messages": [AIMessage(content="[Max iterations reached]")],
                "iteration": iteration + 1,
                "token_count": state["token_count"],
            }

        # Build context: system prompt + optional memory recall + conversation
        context: List[BaseMessage] = [SystemMessage(content=system_prompt)]

        if memory_enabled and messages:
            last_human = next(
                (m.content for m in reversed(messages) if isinstance(m, HumanMessage)), ""
            )
            if last_human:
                memory = get_memory(agent_id, window_size)
                recalled = memory.search_memory(str(last_human), n_results=3)
                if recalled:
                    context.append(SystemMessage(
                        content="[Relevant memory]\n" + "\n".join(recalled)
                    ))

        context.extend(messages)

        # Emit thinking event
        await bus.emit(Event(
            type="agent_thinking",
            execution_id=exec_id,
            agent_id=agent_id,
            payload={"agent_name": agent_name, "iteration": iteration},
        ))

        try:
            response: AIMessage = await llm_with_tools.ainvoke(context)
        except Exception as e:
            logger.error("LLM call failed for %s: %s", agent_name, e)
            response = AIMessage(content=f"Error: {str(e)}")

        # Token tracking
        usage = getattr(response, "usage_metadata", None) or {}
        prompt_tok  = usage.get("input_tokens", 0)
        compl_tok   = usage.get("output_tokens", 0)
        total_tok   = prompt_tok + compl_tok
        cost        = estimate_cost(model_name, prompt_tok, compl_tok)

        # Emit agent_message event
        await bus.emit(Event(
            type="agent_message",
            execution_id=exec_id,
            agent_id=agent_id,
            payload={
                "agent_name": agent_name,
                "content": str(response.content),
                "tool_calls": [tc["name"] for tc in (response.tool_calls or [])],
                "tokens": total_tok,
                "cost_usd": round(cost, 6),
            },
        ))

        # Persist to memory
        if memory_enabled:
            memory = get_memory(agent_id, window_size)
            last_human_msg = next(
                (m for m in reversed(messages) if isinstance(m, HumanMessage)), None
            )
            if last_human_msg:
                memory.add_message("human", str(last_human_msg.content), str(uuid.uuid4()))
            if response.content:
                memory.add_message("assistant", str(response.content), str(uuid.uuid4()))

        return {
            "messages": [response],
            "token_count": state["token_count"] + total_tok,
            "iteration": iteration + 1,
        }

    # ── Tool node ─────────────────────────────────────────────────────────────
    async def tool_node(state: AgentState) -> Dict:
        messages  = state["messages"]
        exec_id   = state["execution_id"]
        last      = messages[-1] if messages else None

        if not isinstance(last, AIMessage) or not last.tool_calls:
            return {"messages": [], "token_count": state["token_count"], "iteration": state["iteration"]}

        tool_messages = await execute_tools(
            last, tools_by_name, exec_id, agent_id, agent_name
        )
        return {
            "messages": tool_messages,
            "token_count": state["token_count"],
            "iteration": state["iteration"],
        }

    # ── Router ────────────────────────────────────────────────────────────────
    def should_continue(state: AgentState) -> str:
        messages  = state["messages"]
        last      = messages[-1] if messages else None
        iteration = state["iteration"]

        if iteration >= max_iter:
            return END
        if isinstance(last, AIMessage) and last.tool_calls and tools:
            return "tools"
        return END

    # ── Build graph ───────────────────────────────────────────────────────────
    graph = StateGraph(AgentState)
    graph.add_node("agent", agent_node)

    if tools:
        graph.add_node("tools", tool_node)
        graph.add_conditional_edges("agent", should_continue, {"tools": "tools", END: END})
        graph.add_edge("tools", "agent")
    else:
        graph.add_conditional_edges("agent", should_continue, {END: END})

    graph.set_entry_point("agent")
    return graph.compile()


# ─── Orchestration Engine ─────────────────────────────────────────────────────

class OrchestrationEngine:
    """
    Central engine — registers agents, runs them, persists results.
    """

    def __init__(self) -> None:
        self._graphs: Dict[str, Any]  = {}   # agent_id → compiled graph
        self._configs: Dict[str, Dict] = {}  # agent_id → config dict

    # ── Registration ──────────────────────────────────────────────────────────

    def register_agent(self, config: Dict[str, Any]) -> None:
        aid = config["id"]
        self._configs[aid] = config
        self._graphs[aid]  = build_agent_graph(config)
        logger.info("Registered agent: %s (%s)", config["name"], aid)

    def unregister_agent(self, agent_id: str) -> None:
        self._graphs.pop(agent_id, None)
        self._configs.pop(agent_id, None)

    # ── Single-agent invocation ───────────────────────────────────────────────

    async def invoke_agent(
        self,
        agent_id: str,
        user_message: str,
        execution_id: Optional[str] = None,
        db=None,
    ) -> str:
        if agent_id not in self._graphs:
            raise ValueError(f"Agent '{agent_id}' not registered.")

        execution_id = execution_id or str(uuid.uuid4())
        config = self._configs[agent_id]

        await bus.emit(Event(
            type="execution_start",
            execution_id=execution_id,
            agent_id=agent_id,
            payload={"agent_name": config["name"], "input": user_message},
        ))

        initial_state: AgentState = {
            "messages":    [HumanMessage(content=user_message)],
            "agent_id":    agent_id,
            "agent_name":  config["name"],
            "execution_id": execution_id,
            "token_count": 0,
            "iteration":   0,
        }

        try:
            final_state = await self._graphs[agent_id].ainvoke(initial_state)

            # Extract final text response
            final_response = ""
            for msg in reversed(final_state.get("messages", [])):
                if isinstance(msg, AIMessage) and msg.content:
                    final_response = str(msg.content)
                    break

            total_tokens = final_state.get("token_count", 0)

            await bus.emit(Event(
                type="execution_complete",
                execution_id=execution_id,
                agent_id=agent_id,
                payload={
                    "agent_name": config["name"],
                    "response": final_response,
                    "total_tokens": total_tokens,
                },
            ))

            if db is not None:
                await self._persist(db, execution_id, agent_id, user_message,
                                    final_response, final_state, config)

            return final_response

        except Exception as e:
            logger.error("Execution failed for agent %s: %s", agent_id, e)
            await bus.emit(Event(
                type="execution_error",
                execution_id=execution_id,
                agent_id=agent_id,
                payload={"error": str(e)},
            ))
            raise

    # ── Agent-by-name (used by send_message_to_agent tool) ───────────────────

    async def invoke_agent_by_name(
        self,
        agent_name: str,
        message: str,
        execution_id: Optional[str] = None,
    ) -> str:
        for aid, cfg in self._configs.items():
            if cfg["name"].lower() == agent_name.lower():
                return await self.invoke_agent(aid, message, execution_id)
        return f"No agent named '{agent_name}' found."

    # ── Workflow invocation ───────────────────────────────────────────────────

    async def invoke_workflow(
        self,
        workflow_config: Dict[str, Any],
        user_message: str,
        execution_id: Optional[str] = None,
        db=None,
    ) -> str:
        """
        Execute a multi-agent workflow.
        The first agent in the graph receives the user message.
        Subsequent agents are reached via send_message_to_agent tool calls.
        """
        execution_id = execution_id or str(uuid.uuid4())

        await bus.emit(Event(
            type="workflow_start",
            execution_id=execution_id,
            payload={
                "workflow_name": workflow_config.get("name"),
                "input": user_message,
            },
        ))

        # Find the entry-point agent
        nodes = workflow_config.get("graph", {}).get("nodes", [])
        entry_agent_id = None
        for node in nodes:
            data = node.get("data", {})
            if data.get("isStart"):
                entry_agent_id = data.get("agentId")
                break
        if entry_agent_id is None and nodes:
            entry_agent_id = nodes[0].get("data", {}).get("agentId")

        if not entry_agent_id or entry_agent_id not in self._graphs:
            # Fallback: run first registered agent
            if self._graphs:
                entry_agent_id = next(iter(self._graphs))
            else:
                raise ValueError("No agents available to run workflow.")

        try:
            response = await self.invoke_agent(
                agent_id=entry_agent_id,
                user_message=user_message,
                execution_id=execution_id,
                db=db,
            )

            await bus.emit(Event(
                type="workflow_complete",
                execution_id=execution_id,
                payload={"response": response},
            ))

            return response

        except Exception as e:
            await bus.emit(Event(
                type="workflow_error",
                execution_id=execution_id,
                payload={"error": str(e)},
            ))
            raise

    # ── DB persistence ────────────────────────────────────────────────────────

    async def _persist(
        self, db, execution_id, agent_id, input_text,
        output_text, final_state, config
    ) -> None:
        from backend.models.execution import Execution, Message

        try:
            total_tokens = final_state.get("token_count", 0)
            model = config.get("model", settings.default_model)
            cost  = estimate_cost(model, total_tokens // 2, total_tokens // 2)

            exec_rec = db.query(Execution).filter(Execution.id == execution_id).first()
            if exec_rec:
                exec_rec.status              = "completed"
                exec_rec.output_text         = output_text
                exec_rec.total_tokens        = total_tokens
                exec_rec.estimated_cost_usd  = f"{cost:.6f}"
                exec_rec.finished_at         = datetime.now(timezone.utc)
            else:
                exec_rec = Execution(
                    id=execution_id,
                    agent_id=agent_id,
                    trigger="api",
                    status="completed",
                    input_text=input_text,
                    output_text=output_text,
                    total_tokens=total_tokens,
                    estimated_cost_usd=f"{cost:.6f}",
                    finished_at=datetime.now(timezone.utc),
                )
                db.add(exec_rec)

            # Persist messages
            for msg in final_state.get("messages", []):
                if isinstance(msg, HumanMessage):
                    role = "human"
                elif isinstance(msg, ToolMessage):
                    role = "tool"
                else:
                    role = "agent"

                content   = str(msg.content) if msg.content else ""
                tool_name = getattr(msg, "name", None) if isinstance(msg, ToolMessage) else None

                db.add(Message(
                    execution_id=execution_id,
                    role=role,
                    content=content,
                    agent_id=agent_id,
                    agent_name=config["name"],
                    tool_name=tool_name,
                ))

            db.commit()
        except Exception as e:
            logger.error("Failed to persist execution %s: %s", execution_id, e)
            db.rollback()


# Global singleton
engine = OrchestrationEngine()
