"""Adaptador de NotificadorMensajes contra Telegram.

Usa el mismo token que el bot de entrada (TELEGRAM_BOT_TOKEN) pero
crea su propio `telegram.Bot`: NotificadorMensajes es un puerto de
salida (avisos que el sistema inicia, ej. confirmaciones de una
reserva), independiente del `Application` de `adapters/in_/telegram_bot.py`
que atiende mensajes entrantes.

`Bot.send_message` es async (python-telegram-bot >= 20); el puerto
`NotificadorMensajes.enviar` es síncrono, así que se ejecuta con
`asyncio.run()`. Pensado para invocarse desde código síncrono (casos de
uso del dominio) fuera de un event loop ya en marcha."""
from __future__ import annotations

import asyncio

from telegram import Bot

from domain.ports import NotificadorMensajes


class NotificadorMensajesTelegram(NotificadorMensajes):
    def __init__(self, token: str):
        self._bot = Bot(token=token)

    def enviar(self, destinatario_id: str, texto: str) -> None:
        asyncio.run(self._bot.send_message(chat_id=destinatario_id, text=texto))
