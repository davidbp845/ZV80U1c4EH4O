"""Implementación concreta del puerto ProveedorLLM usando Cohere.

El resto del sistema (orquestador, sesión de conversación) trabaja con
un formato de mensajes/bloques heredado del wire format de Anthropic
(`{"type": "text"/"tool_use", ...}`, resultados de tool anidados en un
mensaje "user"). La API v2 de Cohere usa una forma estructuralmente
distinta (tools como `{"type": "function", "function": {...}}, mensajes
"tool" dedicados, `tool_plan` + `tool_calls` en el turno del asistente).
Este adaptador es el único sitio que conoce ambos formatos y traduce
entre ellos — ni el dominio ni la aplicación se enteran.
"""
from __future__ import annotations

import json
import os
from collections.abc import Iterator

import cohere

from domain.ports import ProveedorLLM


class ProveedorLLMCohere(ProveedorLLM):
    def __init__(self, modelo: str = "command-r-plus-08-2024", api_key: str | None = None):
        self._client = cohere.ClientV2(api_key=api_key or os.environ["COHERE_API_KEY"])
        self._modelo = modelo

    def generar_respuesta(
        self,
        mensajes: list[dict],
        herramientas: list[dict] | None = None,
        system: str | None = None,
    ) -> dict:
        respuesta = self._client.chat(
            model=self._modelo,
            messages=self._traducir_historial(mensajes, system),
            tools=self._traducir_herramientas(herramientas) if herramientas else None,
        )
        return {"content": self._normalizar_mensaje(respuesta.message)}

    def generar_respuesta_stream(
        self,
        mensajes: list[dict],
        herramientas: list[dict] | None = None,
        system: str | None = None,
    ) -> Iterator[dict]:
        stream = self._client.chat_stream(
            model=self._modelo,
            messages=self._traducir_historial(mensajes, system),
            tools=self._traducir_herramientas(herramientas) if herramientas else None,
        )

        texto = ""
        tool_calls: dict[int, dict] = {}

        for evento in stream:
            if evento.type == "content-delta":
                fragmento = evento.delta.message.content.text
                texto += fragmento
                yield {"tipo": "delta_texto", "texto": fragmento}
            elif evento.type == "tool-call-start":
                tc = evento.delta.message.tool_calls
                tool_calls[evento.index] = {
                    "id": tc.id,
                    "name": tc.function.name,
                    "arguments": tc.function.arguments or "",
                }
            elif evento.type == "tool-call-delta":
                tool_calls[evento.index]["arguments"] += (
                    evento.delta.message.tool_calls.function.arguments or ""
                )
            elif evento.type == "message-end":
                break

        # A diferencia del adaptador de Anthropic, Cohere no expone un
        # "mensaje final" ya ensamblado: el bloque final se reconstruye
        # a partir de lo acumulado en los propios eventos del stream.
        if tool_calls:
            content = [
                {
                    "type": "tool_use",
                    "id": datos["id"],
                    "name": datos["name"],
                    "input": json.loads(datos["arguments"]) if datos["arguments"] else {},
                }
                for _, datos in sorted(tool_calls.items())
            ]
        else:
            content = [{"type": "text", "text": texto}]

        yield {"tipo": "final", "content": content}

    @staticmethod
    def _traducir_herramientas(herramientas: list[dict]) -> list[dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": h["name"],
                    "description": h["description"],
                    "parameters": h["input_schema"],
                },
            }
            for h in herramientas
        ]

    @staticmethod
    def _traducir_historial(mensajes: list[dict], system: str | None) -> list[dict]:
        traducidos = []
        if system:
            traducidos.append({"role": "system", "content": system})

        for mensaje in mensajes:
            contenido = mensaje["content"]

            if mensaje["role"] == "user" and isinstance(contenido, list):
                # Turno de resultados de tool: Anthropic los anida todos en
                # un único mensaje "user"; Cohere usa un mensaje "tool"
                # dedicado por cada resultado.
                for bloque in contenido:
                    traducidos.append({
                        "role": "tool",
                        "tool_call_id": bloque["tool_use_id"],
                        "content": bloque["content"],
                    })

            elif mensaje["role"] == "user":
                traducidos.append({"role": "user", "content": contenido})

            elif mensaje["role"] == "assistant":
                bloques_tool = [b for b in contenido if b["type"] == "tool_use"]
                bloques_texto = [b for b in contenido if b["type"] == "text"]
                texto = "\n".join(b["text"] for b in bloques_texto)

                if bloques_tool:
                    traducidos.append({
                        "role": "assistant",
                        "tool_plan": texto or None,
                        "tool_calls": [
                            {
                                "id": b["id"],
                                "type": "function",
                                "function": {
                                    "name": b["name"],
                                    "arguments": json.dumps(b["input"]),
                                },
                            }
                            for b in bloques_tool
                        ],
                    })
                else:
                    traducidos.append({"role": "assistant", "content": texto})

        return traducidos

    @staticmethod
    def _normalizar_mensaje(mensaje) -> list[dict]:
        bloques = [
            {"type": "text", "text": item.text}
            for item in (mensaje.content or [])
            if item.type == "text"
        ]
        bloques += [
            {
                "type": "tool_use",
                "id": tc.id,
                "name": tc.function.name,
                "input": json.loads(tc.function.arguments) if tc.function.arguments else {},
            }
            for tc in (mensaje.tool_calls or [])
        ]
        return bloques
