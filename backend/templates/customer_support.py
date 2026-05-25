"""
Pre-built Template: Customer Support Triage Workflow

Flow:
  Triage Agent → (classifies issue) → Support Agent or Escalation Agent
"""
from __future__ import annotations

TEMPLATE = {
    "name": "Customer Support Triage",
    "description": (
        "A two-agent workflow where a Triage Agent classifies incoming customer "
        "issues and routes them to either a Support Agent (for common issues) or "
        "an Escalation Agent (for complex/billing issues)."
    ),
    "is_template": True,
    "template_name": "customer_support",
    "graph": {
        "nodes": [
            {
                "id": "triage",
                "type": "agent",
                "position": {"x": 100, "y": 200},
                "data": {
                    "label": "Triage Agent",
                    "agentName": "Triage Agent",
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
                    "isStart": True,
                    "color": "#6366f1",
                },
            },
            {
                "id": "support",
                "type": "agent",
                "position": {"x": 500, "y": 100},
                "data": {
                    "label": "Support Agent",
                    "agentName": "Support Agent",
                    "role": "Technical Support Specialist",
                    "system_prompt": (
                        "You are a friendly and knowledgeable technical support specialist. "
                        "Provide clear, step-by-step solutions to customer issues. "
                        "Use web_search if you need to look up specific technical information. "
                        "Always end with: 'Is there anything else I can help you with?'"
                    ),
                    "tools": ["web_search", "get_current_datetime"],
                    "color": "#10b981",
                },
            },
            {
                "id": "escalation",
                "type": "agent",
                "position": {"x": 500, "y": 350},
                "data": {
                    "label": "Escalation Agent",
                    "agentName": "Escalation Agent",
                    "role": "Senior Support & Billing Specialist",
                    "system_prompt": (
                        "You are a senior support specialist handling billing and urgent issues. "
                        "Be empathetic, professional, and solution-focused. "
                        "For billing issues, explain policies clearly and offer concrete resolutions. "
                        "For urgent issues, acknowledge the urgency and provide immediate next steps. "
                        "Always provide a case reference number (generate a random 6-digit number)."
                    ),
                    "tools": ["calculator", "get_current_datetime"],
                    "color": "#f59e0b",
                },
            },
        ],
        "edges": [
            {"id": "e1", "source": "triage", "target": "support", "label": "Technical/General"},
            {"id": "e2", "source": "triage", "target": "escalation", "label": "Billing/Urgent"},
        ],
    },
}
