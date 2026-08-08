"""Implementación concreta del puerto ProveedorLLM usando OpenAI (ChatGPT).

El resto del sistema trabaja con el formato de mensajes/bloques heredado
del wire format de Anthropic (`{"type": "text"/"tool_use", ...}`,
resultados de tool anidados en un mensaje "user"). La Chat Completions
API de OpenAI usa una forma estructuralmente distinta (tools como
`{"type": "function", "function": {...}}`, mensajes "tool" dedicados
con `tool_call_id`, `tool_calls` en el turno del asistente en vez de
bloques de contenido mezclados con texto). Este adaptador es el único
sitio que conoce ambos formatos y traduce entre ellos — ni el dominio
ni la aplicación se enteran.
"""
from __future__ import annotations

import json
import os
from collections.abc import Iterator

from openai import OpenAI

from domain.ports import ProveedorLLM


class ProveedorLLMOpenAI(ProveedorLLM):
    def __init__(self, modelo: str = "gpt-4o", api_key: str | None = None):
        self._client = OpenAI(api_key=api_key or os.environ["OPENAI_API_KEY"])
        self._modelo = modelo

    def generar_respuesta(
        self,
        mensajes: list[dict],
        herramientas: list[dict] | None = None,
        system: str | None = None,
    ) -> dict:
        respuesta = self._client.chat.completions.create(
            model=self._modelo,
            messages=self._traducir_historial(mensajes, system),
            tools=self._traducir_herramientas(herramientas) if herramientas else None,
            temperature=0,
        )
        return {"content": self._normalizar_mensaje(respuesta.choices[0].message)}

    def generar_respuesta_stream(
        self,
        mensajes: list[dict],
        herramientas: list[dict] | None = None,
        system: str | None = None,
    ) -> Iterator[dict]:
        stream = self._client.chat.completions.create(
            model=self._modelo,
            messages=self._traducir_historial(mensajes, system),
            tools=self._traducir_herramientas(herramientas) if herramientas else None,
            temperature=0,
            stream=True,
        )

        texto = ""
        tool_calls: dict[int, dict] = {}

        for chunk in stream:
            delta = chunk.choices[0].delta
            if delta.content:
                texto += delta.content
                yield {"tipo": "delta_texto", "texto": delta.content}
            for tc in delta.tool_calls or []:
                acumulado = tool_calls.setdefault(tc.index, {"id": None, "name": None, "arguments": ""})
                if tc.id:
                    acumulado["id"] = tc.id
                if tc.function and tc.function.name:
                    acumulado["name"] = tc.function.name
                if tc.function and tc.function.arguments:
                    acumulado["arguments"] += tc.function.arguments

        # A diferencia del adaptador de Anthropic, OpenAI no expone un
        # "mensaje final" ya ensamblado en modo stream: el bloque final
        # se reconstruye a partir de lo acumulado en los propios chunks.
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
                # un único mensaje "user"; OpenAI usa un mensaje "tool"
                # dedicado por cada resultado, referenciado por tool_call_id.
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
                        "content": texto or None,
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
        bloques = []
        if mensaje.content:
            bloques.append({"type": "text", "text": mensaje.content})
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
