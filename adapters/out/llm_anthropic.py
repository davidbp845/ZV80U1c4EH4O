"""Implementación concreta del puerto ProveedorLLM usando Anthropic.
Cambiar de proveedor = escribir otra clase que cumpla el mismo puerto."""
from __future__ import annotations

import os

from anthropic import Anthropic

from domain.ports import ProveedorLLM


class ProveedorLLMAnthropic(ProveedorLLM):
    def __init__(self, modelo: str = "claude-sonnet-5", api_key: str | None = None):
        self._client = Anthropic(api_key=api_key or os.environ["ANTHROPIC_API_KEY"])
        self._modelo = modelo

    def generar_respuesta(
        self,
        mensajes: list[dict],
        herramientas: list[dict] | None = None,
        system: str | None = None,
    ) -> dict:
        respuesta = self._client.messages.create(
            model=self._modelo,
            max_tokens=1024,
            system=system or "",
            messages=mensajes,
            tools=herramientas or [],
        )
        # Normalizamos a dict plano para no acoplar el resto del sistema
        # al SDK de Anthropic (así el orquestador es agnóstico del SDK).
        return {
            "content": [
                {"type": b.type, **b.model_dump()}
                for b in respuesta.content
            ]
        }
