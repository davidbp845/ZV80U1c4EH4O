import asyncio
from unittest.mock import AsyncMock, MagicMock

from telegram.ext import MessageHandler

from adapters.in_ import telegram_bot
from adapters.in_.telegram_bot import crear_bot


class FakeOrquestador:
    def __init__(self, respuesta="Hola desde Telegram"):
        self.respuesta = respuesta
        self.llamadas = []

    def responder(self, sesion, mensaje):
        self.llamadas.append((sesion.canal, sesion.usuario_id, mensaje))
        return self.respuesta


def _obtener_callback(bot_app):
    handlers = bot_app.handlers[0]
    assert len(handlers) == 1
    assert isinstance(handlers[0], MessageHandler)
    return handlers[0].callback


def test_crear_bot_registra_un_unico_message_handler():
    bot_app = crear_bot("fake-token", FakeOrquestador())
    _obtener_callback(bot_app)  # no debe lanzar


def test_manejar_mensaje_responde_usando_el_orquestador():
    telegram_bot._sesiones.clear()
    orquestador = FakeOrquestador()
    bot_app = crear_bot("fake-token", orquestador)
    callback = _obtener_callback(bot_app)

    update = MagicMock()
    update.effective_user.id = 42
    update.message.text = "hola bot"
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    asyncio.run(callback(update, context))

    assert orquestador.llamadas == [("telegram", "42", "hola bot")]
    update.message.reply_text.assert_awaited_once_with(orquestador.respuesta)


def test_manejar_mensaje_reutiliza_sesion_del_mismo_usuario():
    telegram_bot._sesiones.clear()
    orquestador = FakeOrquestador()
    bot_app = crear_bot("fake-token", orquestador)
    callback = _obtener_callback(bot_app)

    update = MagicMock()
    update.effective_user.id = 99
    update.message.reply_text = AsyncMock()
    context = MagicMock()

    update.message.text = "primero"
    asyncio.run(callback(update, context))
    update.message.text = "segundo"
    asyncio.run(callback(update, context))

    assert len(telegram_bot._sesiones) == 1
    assert [m for _, _, m in orquestador.llamadas] == ["primero", "segundo"]
