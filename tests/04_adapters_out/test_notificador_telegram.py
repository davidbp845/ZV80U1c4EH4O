from unittest.mock import AsyncMock, patch

from adapters.out.notificador_telegram import NotificadorMensajesTelegram


def test_enviar_llama_a_send_message_con_chat_id_y_texto():
    with patch("telegram.Bot.send_message", new_callable=AsyncMock) as mock_send_message:
        notificador = NotificadorMensajesTelegram(token="123:abc")
        notificador.enviar("987654321", "Tu reserva ha sido confirmada.")

        mock_send_message.assert_awaited_once_with(
            chat_id="987654321", text="Tu reserva ha sido confirmada."
        )
