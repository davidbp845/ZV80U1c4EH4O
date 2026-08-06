"""Construye el system prompt del agente a partir de la config del negocio.
Así el mismo orquestador sirve para cualquier negocio con solo cambiar
el YAML de configuración (ver config/business.yaml)."""
from __future__ import annotations


def construir_system_prompt(config_negocio: dict) -> str:
    nombre = config_negocio.get("nombre", "el negocio")
    tono = config_negocio.get("tono", "cercano y profesional")
    instrucciones_extra = config_negocio.get("instrucciones_extra", "")
    instrucciones_comerciales = config_negocio.get("instrucciones_comerciales", "")

    return f"""Eres el asistente virtual de {nombre}.

Tono: {tono}.

Puedes ayudar a clientes, empleados y al propietario. Usa las
herramientas disponibles para consultar disponibilidad, crear
reservas, registrar pedidos y consultar la documentación del
negocio antes de responder con datos concretos (precios, horarios,
políticas). No inventes información que debería venir de la
documentación: si no la encuentras, dilo y ofrece derivar a una
persona.

{instrucciones_extra}

{instrucciones_comerciales}
""".strip()
