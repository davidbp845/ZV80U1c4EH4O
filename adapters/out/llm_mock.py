"""Implementación de prueba del puerto ProveedorLLM, para desarrollar
el frontend (o cualquier cliente del chat) sin gastar tokens de la
API real de Anthropic. Simula, con heurísticas simples sobre el
último mensaje de la conversación, los tipos de respuesta que el
orquestador sabe manejar: petición de una tool, texto tras el
resultado de una tool, y texto libre. Activar con USE_MOCK_LLM=true
(ver main.py y .env.example)."""
from __future__ import annotations

import random
import uuid
from collections.abc import Iterator
from datetime import date, timedelta

from domain.ports import ProveedorLLM

_RESPUESTAS_EJEMPLO = [
    "¡Hola! Soy el asistente del centro. ¿En qué puedo ayudarte hoy?",
    (
        "Tenemos dos servicios disponibles: masaje relajante de 60 "
        "minutos (55€) y masaje descontracturante de 45 minutos (48€). "
        "¿Cuál te interesa?"
    ),
    (
        "Recuerda que puedes cancelar o cambiar tu cita sin coste hasta "
        "4 horas antes de la hora reservada; con menos antelación se "
        "aplica un cargo del 50% del servicio, y las no presentaciones "
        "se cobran al 100%."
    ),
    (
        "Ana es nuestra terapeuta titulada, con más de 10 años de "
        "experiencia en masaje relajante y descontracturante. Trabaja de "
        "lunes a viernes (los viernes solo por la mañana)."
    ),
    (
        "No he encontrado esa información en la documentación del "
        "negocio. ¿Puedes darme más detalles o prefieres que te "
        "derive a una persona?"
    ),
]


class ProveedorLLMMock(ProveedorLLM):
    """Simula respuestas de un LLM sin llamar a ningún servicio externo."""

    def generar_respuesta(
        self,
        mensajes: list[dict],
        herramientas: list[dict] | None = None,
        system: str | None = None,
    ) -> dict:
        ultimo_mensaje = mensajes[-1] if mensajes else {}
        contenido = ultimo_mensaje.get("content", "")

        if isinstance(contenido, list):
            # El mensaje anterior es un tool_result: el orquestador espera
            # ahora una respuesta en texto que cierre el turno.
            return {"content": [{"type": "text", "text": self._respuesta_tras_tool()}]}

        if isinstance(contenido, str) and self._pide_disponibilidad(contenido):
            return {"content": [self._bloque_tool_use_disponibilidad()]}

        return {"content": [{"type": "text", "text": random.choice(_RESPUESTAS_EJEMPLO)}]}

    def generar_respuesta_stream(
        self,
        mensajes: list[dict],
        herramientas: list[dict] | None = None,
        system: str | None = None,
    ) -> Iterator[dict]:
        # Reutiliza exactamente las mismas heurísticas que generar_respuesta
        # para que el mock en streaming y sin streaming nunca diverjan.
        resultado = self.generar_respuesta(mensajes, herramientas, system)
        bloque = resultado["content"][0]

        if bloque["type"] == "text":
            palabras = bloque["text"].split(" ")
            for i, palabra in enumerate(palabras):
                texto = palabra if i == len(palabras) - 1 else palabra + " "
                yield {"tipo": "delta_texto", "texto": texto}
        # Los tool_use no llevan texto previo: se emiten sin deltas,
        # igual que suele comportarse el modelo real en estos casos.

        yield {"tipo": "final", "content": resultado["content"]}

    @staticmethod
    def _pide_disponibilidad(texto: str) -> bool:
        texto_normalizado = texto.lower()
        return "disponib" in texto_normalizado or "hueco" in texto_normalizado

    @staticmethod
    def _bloque_tool_use_disponibilidad() -> dict:
        fecha_ejemplo = date.today() + timedelta(days=1)
        return {
            "type": "tool_use",
            "id": f"mock_{uuid.uuid4().hex[:8]}",
            "name": "comprobar_disponibilidad",
            "input": {
                "servicio_id": "masaje_relajante_60",
                "fecha": fecha_ejemplo.isoformat(),
            },
        }

    @staticmethod
    def _respuesta_tras_tool() -> str:
        return (
            "He consultado la disponibilidad: tenemos un hueco mañana a "
            "las 10:00 con Ana. ¿Te viene bien esa hora?"
        )
