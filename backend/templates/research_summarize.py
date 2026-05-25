"""
Pre-built Template: Research & Summarize Workflow

Flow:
  Research Agent → (gathers info) → Analyst Agent → (synthesizes) → Writer Agent
"""
from __future__ import annotations

TEMPLATE = {
    "name": "Research & Summarize",
    "description": (
        "A three-agent pipeline: a Research Agent gathers information from the web, "
        "an Analyst Agent synthesizes key insights, and a Writer Agent produces "
        "a polished final report."
    ),
    "is_template": True,
    "template_name": "research_summarize",
    "graph": {
        "nodes": [
            {
                "id": "researcher",
                "type": "agent",
                "position": {"x": 50, "y": 200},
                "data": {
                    "label": "Research Agent",
                    "agentName": "Research Agent",
                    "role": "Research Specialist",
                    "system_prompt": (
                        "You are a thorough research specialist. "
                        "When given a topic, use web_search to gather comprehensive information "
                        "from multiple angles. Search at least 3 different aspects of the topic. "
                        "Compile all findings into a structured research brief with sources. "
                        "Then pass your research to the Analyst Agent using send_message_to_agent."
                    ),
                    "tools": ["web_search", "get_current_datetime", "send_message_to_agent"],
                    "isStart": True,
                    "color": "#3b82f6",
                },
            },
            {
                "id": "analyst",
                "type": "agent",
                "position": {"x": 400, "y": 200},
                "data": {
                    "label": "Analyst Agent",
                    "agentName": "Analyst Agent",
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
                    "color": "#8b5cf6",
                },
            },
            {
                "id": "writer",
                "type": "agent",
                "position": {"x": 750, "y": 200},
                "data": {
                    "label": "Writer Agent",
                    "agentName": "Writer Agent",
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
                    "color": "#ec4899",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "researcher", "target": "analyst", "label": "Research Brief"},
            {"id": "e2", "source": "analyst", "target": "writer", "label": "Analysis"},
        ],
    },
}
