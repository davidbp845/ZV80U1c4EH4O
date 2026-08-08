"""
Adaptador de entrada: bot de Telegram. Igual que el adaptador web,
solo traduce Telegram <-> orquestador. Cero lógica de negocio aquí.
"""
from __future__ import annotations

from telegram import Update
from telegram.ext import (
    Application,
    ContextTypes,
    MessageHandler,
    filters,
)

from application.orchestrator import OrquestadorAgente, SesionConversacion
from application.ports import RepositorioSesiones


def crear_bot(
    token: str, orquestador: OrquestadorAgente, repositorio_sesiones: RepositorioSesiones
) -> Application:
    app = Application.builder().token(token).build()

    async def manejar_mensaje(update: Update, context: ContextTypes.DEFAULT_TYPE):
        usuario_id = str(update.effective_user.id)
        sesion = repositorio_sesiones.obtener("telegram", usuario_id) or SesionConversacion(
            canal="telegram", usuario_id=usuario_id
        )
        respuesta = orquestador.responder(sesion, update.message.text)
        repositorio_sesiones.guardar(sesion)
        await update.message.reply_text(respuesta)

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, manejar_mensaje))
    return app
