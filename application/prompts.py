"""Construye el system prompt del agente a partir de la config del negocio.
Así el mismo orquestador sirve para cualquier negocio con solo cambiar
el YAML de configuración (ver config/business.yaml)."""
from __future__ import annotations


def _construir_catalogo(config_negocio: dict) -> str:
    """Las tools de reserva (comprobar_disponibilidad, crear_reserva)
    exigen servicio_id/profesional_id exactos, no nombres en texto
    libre — sin esto en el prompt, el LLM solo conoce los servicios
    por el nombre humano que aparece en el RAG y adivina el id, lo
    que falla contra el dominio (ServicioNoExiste)."""
    servicios = config_negocio.get("servicios") or []
    profesionales = config_negocio.get("profesionales") or []

    if not servicios and not profesionales:
        return ""

    lineas = [
        "Catálogo de servicios y profesionales — usa siempre estos IDs "
        "exactos (nunca el nombre en texto libre) al llamar a "
        "comprobar_disponibilidad o crear_reserva:",
    ]

    if servicios:
        lineas.append("\nServicios (id — nombre, duración, precio):")
        lineas += [
            f"- {s['id']} — {s['nombre']}, {s['duracion_minutos']} min, {s['precio']}€"
            for s in servicios
        ]

    if profesionales:
        lineas.append("\nProfesionales (id — nombre: servicios que ofrece):")
        lineas += [
            f"- {p['id']} — {p['nombre']}: {', '.join(p.get('servicios_ids', [])) or 'ninguno'}"
            for p in profesionales
        ]

    return "\n".join(lineas)


def construir_system_prompt(config_negocio: dict) -> str:
    nombre = config_negocio.get("nombre", "el negocio")
    tono = config_negocio.get("tono", "cercano y profesional")
    instrucciones_extra = config_negocio.get("instrucciones_extra", "")
    instrucciones_comerciales = config_negocio.get("instrucciones_comerciales", "")
    catalogo = _construir_catalogo(config_negocio)

    return f"""Eres el asistente virtual de {nombre}.

Tono: {tono}.

Puedes ayudar a clientes, empleados y al propietario. Usa las
herramientas disponibles para consultar disponibilidad, crear
reservas, registrar pedidos y consultar la documentación del
negocio antes de responder con datos concretos (precios, horarios,
políticas). No inventes información que debería venir de la
documentación: si no la encuentras, dilo y ofrece derivar a una
persona.

{catalogo}

Al crear una reserva (crear_reserva) necesitas un cliente_id: si el
cliente no te ha dado su teléfono en la conversación, pídeselo (o su
nombre completo si prefiere no darlo) y usa ese dato tal cual como
cliente_id.

{instrucciones_extra}

{instrucciones_comerciales}
""".strip()
