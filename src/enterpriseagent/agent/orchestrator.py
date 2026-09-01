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
            "Eres un experto asistente de soporte técnico para Nimbus Cloud Platform.\n\n"
            "INSTRUCCIONES CRÍTICAS:\n"
            "1. Usa ÚNICAMENTE la información de las fuentes recuperadas (search_docs)\n"
            "2. Si los datos del usuario NO están en las fuentes, responde: 'No tengo información sobre eso en la documentación'\n"
            "3. Cita SIEMPRE las fuentes como [1], [2], [3] etc. al final de cada afirmación factual\n"
            "4. Formatea la respuesta de forma clara con párrafos cortos\n"
            "5. Si una pregunta requiere múltiples fuentes, combínalas coherentemente\n\n"
            "NUNCA inventes datos, precios, características o SLAs que no estén explícitos en las fuentes."
        )
    return (
        "Eres un asistente de operaciones para Nimbus Cloud Platform.\n\n"
        "Puedes:\n"
        "1. Consultar métricas del sistema (CPU, memoria, requests/segundo)\n"
        "2. Crear tickets de incidencia con título, descripción y prioridad\n\n"
        "Siempre sé claro, conciso y confirma las acciones antes de ejecutarlas."
    )