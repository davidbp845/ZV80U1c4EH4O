"""Puertos propios de la capa de aplicación (no del dominio):
SesionConversacion vive en application/orchestrator.py, no en
domain/, así que su puerto de persistencia va aquí en vez de en
domain/ports.py — el dominio no sabe que existen canales de chat ni
sesiones conversacionales, eso es una noción del orquestador.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from .orchestrator import SesionConversacion


class RepositorioSesiones(ABC):
    """Persiste el estado conversacional por canal + usuario. El
    orquestador (OrquestadorAgente.responder/responder_stream) muta
    sesion.historial in-place; el patrón de uso en los adaptadores de
    entrada es: obtener() antes de llamar al orquestador, guardar()
    después, para persistir los cambios de esa vuelta."""

    @abstractmethod
    def obtener(self, canal: str, usuario_id: str) -> SesionConversacion | None: ...

    @abstractmethod
    def guardar(self, sesion: SesionConversacion) -> None: ...
