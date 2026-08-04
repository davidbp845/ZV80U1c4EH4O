"""
Orquestador de agentes: puerto de entrada conversacional. Recibe un
mensaje de cualquier canal (web, Telegram...) junto con el historial,
decide qué herramientas invocar mediante el LLM, ejecuta esas
herramientas contra el dominio, y devuelve una respuesta en lenguaje
natural. Es agnóstico del canal: no sabe si viene de Telegram o web.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from domain.ports import ProveedorLLM
from .tools import TOOLS_SCHEMA, EjecutorHerramientas


@dataclass
class SesionConversacion:
    """Estado conversacional de un usuario concreto (por canal + id)."""
    canal: str
    usuario_id: str
    historial: list[dict] = field(default_factory=list)


class OrquestadorAgente:
    def __init__(
        self,
        llm: ProveedorLLM,
        ejecutor_herramientas: EjecutorHerramientas,
        system_prompt: str,
        max_iteraciones_tool: int = 4,
    ):
        self._llm = llm
        self._ejecutor = ejecutor_herramientas
        self._system_prompt = system_prompt
        self._max_iteraciones = max_iteraciones_tool

    def responder(self, sesion: SesionConversacion, mensaje_usuario: str) -> str:
        sesion.historial.append({"role": "user", "content": mensaje_usuario})

        for _ in range(self._max_iteraciones):
            respuesta = self._llm.generar_respuesta(
                mensajes=sesion.historial,
                herramientas=TOOLS_SCHEMA,
                system=self._system_prompt,
            )

            bloques_tool = [b for b in respuesta["content"] if b["type"] == "tool_use"]
            bloques_texto = [b for b in respuesta["content"] if b["type"] == "text"]

            sesion.historial.append({"role": "assistant", "content": respuesta["content"]})

            if not bloques_tool:
                return "\n".join(b["text"] for b in bloques_texto)

            resultados_tool = []
            for bloque in bloques_tool:
                resultado = self._ejecutor.ejecutar(bloque["name"], bloque["input"])
                resultados_tool.append({
                    "type": "tool_result",
                    "tool_use_id": bloque["id"],
                    "content": str(resultado),
                })

            sesion.historial.append({"role": "user", "content": resultados_tool})

        return (
            "Lo siento, no he podido completar la solicitud. "
            "¿Puedes reformularla o contactar directamente con el negocio?"
        )
