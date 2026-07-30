from __future__ import annotations

from dataclasses import dataclass


@dataclass
class EvalItem:
    question: str
    expected_answer: str
    expected_sources: list[str]
    category: str


EVAL_DATASET: list[EvalItem] = [
    # ── Factual directa (15) ──────────────────────────────────────────
    EvalItem(
        question="Cual es el SLA del plan Enterprise?",
        expected_answer="99.99% de disponibilidad mensual",
        expected_sources=["slas.md"],
        category="factual",
    ),
    EvalItem(
        question="Cual es el precio del plan Pro?",
        expected_answer="$29 por mes",
        expected_sources=["pricing.md"],
        category="factual",
    ),
    EvalItem(
        question="Cuantas apps incluye el plan Free?",
        expected_answer="1 app concurrente",
        expected_sources=["pricing.md"],
        category="factual",
    ),
    EvalItem(
        question="Que metodos de autenticacion soporta Nimbus?",
        expected_answer="API keys y OAuth2",
        expected_sources=["authentication.md"],
        category="factual",
    ),
    EvalItem(
        question="Cual es la URL base de la API de Nimbus?",
        expected_answer="https://api.nimbus.example.com/v1",
        expected_sources=["api-reference.md"],
        category="factual",
    ),
    EvalItem(
        question="Que runtimes soporta Nimbus?",
        expected_answer="Node.js, Python, Go, Rust y cualquier app containerizada via Dockerfile",
        expected_sources=["faq.md"],
        category="factual",
    ),
    EvalItem(
        question="Cual es el tiempo de respuesta para severidad 1 en el plan Enterprise?",
        expected_answer="15 minutos",
        expected_sources=["slas.md"],
        category="factual",
    ),
    EvalItem(
        question="Como se despliega una app con Nimbus?",
        expected_answer="Con el comando 'nimbus deploy'",
        expected_sources=["getting-started.md"],
        category="factual",
    ),
    EvalItem(
        question="Cuantas regiones tiene la red global de Nimbus?",
        expected_answer="30 regiones a nivel mundial",
        expected_sources=["index.md"],
        category="factual",
    ),
    EvalItem(
        question="Que prefijo tienen las API keys de Nimbus?",
        expected_answer="nmb_",
        expected_sources=["authentication.md"],
        category="factual",
    ),
    EvalItem(
        question="Cual es el addon de PostgreSQL en Nimbus?",
        expected_answer="$15/mes por base de datos con 10 GB de almacenamiento",
        expected_sources=["pricing.md"],
        category="factual",
    ),
    EvalItem(
        question="Cuantos entornos soporta Nimbus por proyecto?",
        expected_answer="Tres: development, staging y production",
        expected_sources=["getting-started.md"],
        category="factual",
    ),
    EvalItem(
        question="Cual es el codigo de error HTTP para rate limited en Nimbus?",
        expected_answer="429",
        expected_sources=["troubleshooting.md"],
        category="factual",
    ),
    EvalItem(
        question="Que metodos de pago acepta Nimbus?",
        expected_answer="Tarjetas de credito (Visa, Mastercard, Amex) y PayPal. Planes Enterprise tambien por factura",
        expected_sources=["faq.md"],
        category="factual",
    ),
    EvalItem(
        question="Que encriptacion usa Nimbus para datos en reposo?",
        expected_answer="AES-256",
        expected_sources=["faq.md"],
        category="factual",
    ),
    # ── Sintetica (10) ────────────────────────────────────────────────
    EvalItem(
        question="Que plan me recomiendas para una empresa con 50 empleados que necesita mas de 10 apps y soporte prioritario?",
        expected_answer="El plan Enterprise a $99/mes, que incluye apps ilimitadas, 1 TB de ancho de banda y soporte prioritario con respuesta en 1 hora",
        expected_sources=["pricing.md", "slas.md"],
        category="synthetic",
    ),
    EvalItem(
        question="Como obtengo una API key y que hago con ella?",
        expected_answer="Se genera en el Dashboard en Settings > API Keys, tiene prefijo nmb_, y se incluye en el header Authorization: Bearer nmb_...",
        expected_sources=["authentication.md"],
        category="synthetic",
    ),
    EvalItem(
        question="Si mi app esta lenta, que pasos debo seguir?",
        expected_answer="1) Revisar CPU y memoria con 'nimbus metrics', 2) considerar instancia dedicada, 3) habilitar auto-scaling, 4) verificar limites de rate limiting",
        expected_sources=["troubleshooting.md", "index.md"],
        category="synthetic",
    ),
    EvalItem(
        question="Cual es la diferencia entre los planes Free y Pro en soporte?",
        expected_answer="Free solo tiene soporte comunitario. Pro tiene soporte por email con respuesta en 4 horas, y para severidad 1 responde en 2 horas",
        expected_sources=["pricing.md", "slas.md"],
        category="synthetic",
    ),
    EvalItem(
        question="Cuantas API keys puedo tener y a que entornos pueden estar limitadas?",
        expected_answer="Cada proyecto puede tener hasta 5 API keys, y pueden tener ambito (scoped) a entornos especificos",
        expected_sources=["authentication.md"],
        category="synthetic",
    ),
    EvalItem(
        question="Que pasa si supero el limite de mi plan?",
        expected_answer="Se pueden establecer limites de gasto en el Dashboard. Por defecto las peticiones que exceden el limite reciben un 429",
        expected_sources=["faq.md", "authentication.md"],
        category="synthetic",
    ),
    EvalItem(
        question="Como escalar una app y que metrica activa el auto-scaling?",
        expected_answer="Se escala con 'nimbus scale --min 2 --max 10'. El auto-scaling ajusta basado en CPU y latencia de peticiones",
        expected_sources=["faq.md", "troubleshooting.md"],
        category="synthetic",
    ),
    EvalItem(
        question="Que incluye el plan Enterprise ademas de apps ilimitadas?",
        expected_answer="1 TB de ancho de banda, 10 millones de peticiones, dominios personalizados ilimitados, soporte prioritario con respuesta en 1 hora, account manager dedicado y negociacion de SLA personalizada",
        expected_sources=["pricing.md", "slas.md"],
        category="synthetic",
    ),
    EvalItem(
        question="Donde se despliega mi app y como acceder a ella?",
        expected_answer="Se despliega con 'nimbus deploy' y queda disponible en https://[app-name].nimbus.example.com en menos de 30 segundos",
        expected_sources=["getting-started.md"],
        category="synthetic",
    ),
    EvalItem(
        question="Como verifico el estado de un deployment?",
        expected_answer="Con el endpoint GET /apps/:id/deployments/:deploy_id de la API, o con 'nimbus deployments --latest' desde la CLI",
        expected_sources=["api-reference.md", "troubleshooting.md"],
        category="synthetic",
    ),
    # ── Sin respuesta en docs (10) ────────────────────────────────────
    EvalItem(
        question="Quien fundo Nimbus?",
        expected_answer="No tengo informacion sobre quien fundo Nimbus",
        expected_sources=[],
        category="no_answer",
    ),
    EvalItem(
        question="En que ano se fundo Nimbus?",
        expected_answer="No tengo informacion sobre el ano de fundacion de Nimbus",
        expected_sources=[],
        category="no_answer",
    ),
    EvalItem(
        question="Cual es la mision de Nimbus?",
        expected_answer="No tengo informacion sobre la mision de Nimbus",
        expected_sources=[],
        category="no_answer",
    ),
    EvalItem(
        question="Quien es el CEO de Nimbus?",
        expected_answer="No tengo informacion sobre el CEO de Nimbus",
        expected_sources=[],
        category="no_answer",
    ),
    EvalItem(
        question="Donde estan las oficinas de Nimbus?",
        expected_answer="No tengo informacion sobre las oficinas de Nimbus",
        expected_sources=[],
        category="no_answer",
    ),
    EvalItem(
        question="Cuantos empleados tiene Nimbus?",
        expected_answer="No tengo informacion sobre la cantidad de empleados de Nimbus",
        expected_sources=[],
        category="no_answer",
    ),
    EvalItem(
        question="Nimbus tiene integracion con Slack?",
        expected_answer="No tengo informacion sobre integracion con Slack",
        expected_sources=[],
        category="no_answer",
    ),
    EvalItem(
        question="Cual es la version mas reciente de Nimbus?",
        expected_answer="No tengo informacion sobre versiones de Nimbus",
        expected_sources=[],
        category="no_answer",
    ),
    EvalItem(
        question="Nimbus ofrece servicio de email?",
        expected_answer="No tengo informacion sobre servicio de email",
        expected_sources=[],
        category="no_answer",
    ),
    EvalItem(
        question="Que lenguaje de programacion uso Nimbus internamente?",
        expected_answer="No tengo informacion sobre la implementacion interna de Nimbus",
        expected_sources=[],
        category="no_answer",
    ),
    # ── Borde / ambiguas (5) ──────────────────────────────────────────
    EvalItem(
        question="El plan Free es suficiente para produccion?",
        expected_answer="El plan Free tiene limitaciones importantes: 1 app, 10 GB de ancho de banda, sin dominio personalizado y sin SLA. No se recomienda para produccion",
        expected_sources=["pricing.md", "slas.md"],
        category="edge",
    ),
    EvalItem(
        question="Puedo tener 15 apps en el plan Pro?",
        expected_answer="No, el plan Pro incluye 10 apps concurrentes. Habria que contratar Enterprise que tiene apps ilimitadas",
        expected_sources=["pricing.md"],
        category="edge",
    ),
    EvalItem(
        question="Que pasa si mi app supera 1 TB de ancho de banda en Enterprise?",
        expected_answer="Se pueden anyadir paquetes de ancho de banda adicional a $10 por 100 GB, o configurar limites de gasto en el Dashboard",
        expected_sources=["pricing.md", "faq.md"],
        category="edge",
    ),
    EvalItem(
        question="Nimbus ofrece descuento por facturacion anual?",
        expected_answer="Si, la facturacion anual tiene un 20% de descuento sobre el precio mensual",
        expected_sources=["faq.md", "pricing.md"],
        category="edge",
    ),
    EvalItem(
        question="Puedo cambiar de plan mas de una vez?",
        expected_answer="Si, se puede actualizar o degradar el plan en cualquier momento desde el Dashboard, y los cambios son inmediatos",
        expected_sources=["faq.md"],
        category="edge",
    ),
]
