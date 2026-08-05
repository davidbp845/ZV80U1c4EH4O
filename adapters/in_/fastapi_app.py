"""
Adaptador de entrada: expone el orquestador de agentes vía HTTP para
el chat de la web. No contiene lógica de negocio, solo traduce
HTTP <-> orquestador.
"""
from __future__ import annotations

import json

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from application.orchestrator import OrquestadorAgente, SesionConversacion

app = FastAPI(title="Orquestador agéntico — chat web")

# Orígenes de dev habituales (Vite, alternativa común en 3000; 4321 es
# el puerto por defecto de Astro) para que un frontend en desarrollo
# pueda llamar al backend sin bloqueo CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:3000",
        "http://localhost:4321",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

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

    @app.post("/chat/stream")
    def chat_stream(payload: MensajeEntrante):
        sesion = _sesiones.setdefault(
            payload.usuario_id,
            SesionConversacion(canal="web", usuario_id=payload.usuario_id),
        )

        def eventos_sse():
            try:
                for evento in orquestador.responder_stream(sesion, payload.mensaje):
                    if evento["tipo"] == "delta":
                        yield f"event: delta\ndata: {json.dumps({'texto': evento['texto']})}\n\n"
                    elif evento["tipo"] == "done":
                        yield f"event: fuentes\ndata: {json.dumps({'fuentes': evento['fuentes']})}\n\n"
                        yield f"event: done\ndata: {json.dumps({'respuesta': evento['respuesta']})}\n\n"
            except Exception as exc:  # noqa: BLE001 — un fallo se convierte en un evento, no en una conexión cortada
                yield f"event: error\ndata: {json.dumps({'mensaje': str(exc)})}\n\n"

        return StreamingResponse(
            eventos_sse(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    return app
