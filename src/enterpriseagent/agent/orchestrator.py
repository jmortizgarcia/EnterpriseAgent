from enterpriseagent.agent.tools.base import Tool

DOCS_TOOLS = {"search_docs"}
ACTION_TOOLS = {"create_ticket", "query_metric"}

INTENT_KEYWORDS: dict[str, list[str]] = {
    "documentation": [
        "qué es", "cómo", "precio", "sla", "plan", "documentación", "guía",
        "tutorial", "ejemplo", "faq", "precios", "enterprise", "pro", "free",
        "api", "autenticación", "troubleshooting", "getting started",
        "soporte", "service", "acuerdo", "nivel", "sla",
    ],
    "action": [
        "ticket", "crea", "crear", "métrica", "cpu", "memoria",
        "requests", "alerta", "notificar", "monitor", "abrir", "reportar",
        "incidencia", "problema técnico", "rendimiento",
    ],
}


def classify_intent(message: str) -> str:
    msg_lower = message.lower()
    doc_score = sum(1 for kw in INTENT_KEYWORDS["documentation"] if kw in msg_lower)
    action_score = sum(1 for kw in INTENT_KEYWORDS["action"] if kw in msg_lower)
    if action_score > doc_score:
        return "action"
    return "documentation"


def filter_tools_for_intent(tools: list[Tool], intent: str) -> list[Tool]:
    if intent == "documentation":
        selected = [t for t in tools if t.name in DOCS_TOOLS]
        # include any tool not explicitly categorized
        selected.extend(t for t in tools if t.name not in DOCS_TOOLS and t.name not in ACTION_TOOLS)
        return selected
    if intent == "action":
        selected = [t for t in tools if t.name in ACTION_TOOLS]
        selected.extend(t for t in tools if t.name not in DOCS_TOOLS and t.name not in ACTION_TOOLS)
        return selected
    return tools


def supervisor_prompt(intent: str) -> str:
    if intent == "documentation":
        return (
            "Eres un asistente de soporte técnico para Nimbus Cloud Platform. "
            "Tus respuestas deben basarse SOLO en las fuentes proporcionadas por search_docs. "
            "Cita las fuentes como [1], [2], etc. Si no hay información, dilo explícitamente."
        )
    return (
        "Eres un asistente de operaciones. Puedes consultar métricas del sistema "
        "y crear tickets de incidencia. Responde de forma clara y concisa."
    )