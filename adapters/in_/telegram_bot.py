"""
Adaptador de entrada: bot de Telegram. Igual que el adaptador web,
solo traduce Telegram <-> orquestador. Cero lógica de negocio aquí.
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import (
    Application, ContextTypes, MessageHandler, filters,
)

from application.orchestrator import OrquestadorAgente, SesionConversacion

_sesiones: dict[str, SesionConversacion] = {}


def crear_bot(token: str, orquestador: OrquestadorAgente) -> Application:
    app = Application.builder().token(token).build()

    async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
        usuario_id = str(update.effective_user.id)
        sesion = _sesiones.setdefault(
            usuario_id,
            SesionConversacion(canal="telegram", usuario_id=usuario_id),
        )
        respuesta = orquestador.responder(sesion, update.message.text)
        await update.message.reply_text(respuesta)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    return app
