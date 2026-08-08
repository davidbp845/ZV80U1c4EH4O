"""Implementación en memoria de RepositorioSesiones. Comportamiento
equivalente al de los `_sesiones: dict` que antes vivían directamente
en adapters/in_/fastapi_app.py y adapters/in_/telegram_bot.py — no
sobrevive a un reinicio del proceso ni se comparte entre procesos.
Sirve para desarrollo y tests sin necesidad de levantar Redis; ver
RepositorioSesionesRedis para la alternativa persistente."""
from __future__ import annotations

from application.orchestrator import SesionConversacion
from application.ports import RepositorioSesiones


class RepositorioSesionesMemoria(RepositorioSesiones):
    def __init__(self):
        self._data: dict[tuple[str, str], SesionConversacion] = {}

    def obtener(self, canal: str, usuario_id: str) -> SesionConversacion | None:
        return self._data.get((canal, usuario_id))

    def guardar(self, sesion: SesionConversacion) -> None:
        self._data[(sesion.canal, sesion.usuario_id)] = sesion
