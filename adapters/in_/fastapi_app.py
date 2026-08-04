"""
Adaptador de entrada: expone el orquestador de agentes vía HTTP para
el chat de la web. No contiene lógica de negocio, solo traduce
HTTP <-> orquestador.
"""
from __future__ import annotations

from fastapi import FastAPI
from pydantic import BaseModel

from application.orchestrator import OrquestadorAgente, SesionConversacion

app = FastAPI(title="Orquestador agéntico — chat web")

# En producción, las sesiones deberían persistirse (Redis, DB) en vez
# de vivir en memoria del proceso.
_sesiones: dict[str, SesionConversacion] = {}


class MensajeEntrante(BaseModel):
    usuario_id: str
    mensaje: str


class RespuestaAgente(BaseModel):
    respuesta: str


def crear_router(orquestador: OrquestadorAgente) -> FastAPI:
    @app.post("/chat", response_model=RespuestaAgente)
    def chat(payload: MensajeEntrante):
        sesion = _sesiones.setdefault(
            payload.usuario_id,
            SesionConversacion(canal="web", usuario_id=payload.usuario_id),
        )
        respuesta = orquestador.responder(sesion, payload.mensaje)
        return RespuestaAgente(respuesta=respuesta)

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
