"""Implementación de RepositorioSesiones sobre Redis: persiste el
historial de conversación como JSON, para que sobreviva a un reinicio
del proceso y se comparta entre varios workers/procesos. Alternativa
a RepositorioSesionesMemoria, seleccionada en main.py cuando hay
REDIS_URL configurada."""
from __future__ import annotations

import json

from redis import Redis

from application.orchestrator import SesionConversacion
from application.ports import RepositorioSesiones


class RepositorioSesionesRedis(RepositorioSesiones):
    def __init__(self, redis_url: str, cliente: Redis | None = None):
        self._cliente = cliente or Redis.from_url(redis_url, decode_responses=True)

    def obtener(self, canal: str, usuario_id: str) -> SesionConversacion | None:
        bruto = self._cliente.get(self._clave(canal, usuario_id))
        if bruto is None:
            return None
        return SesionConversacion(canal=canal, usuario_id=usuario_id, historial=json.loads(bruto))

    def guardar(self, sesion: SesionConversacion) -> None:
        self._cliente.set(
            self._clave(sesion.canal, sesion.usuario_id),
            json.dumps(sesion.historial),
        )

    @staticmethod
    def _clave(canal: str, usuario_id: str) -> str:
        return f"sesion:{canal}:{usuario_id}"
