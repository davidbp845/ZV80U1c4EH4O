from unittest.mock import MagicMock, patch

from adapters.out.llm_anthropic import ProveedorLLMAnthropic


class _BloqueFalso:
    """Imita un bloque de contenido del SDK de Anthropic (TextBlock,
    ToolUseBlock...): tiene `.type` y `.model_dump()`."""

    def __init__(self, type_, **datos):
        self.type = type_
        self._datos = {"type": type_, **datos}

    def model_dump(self):
        return self._datos


def _proveedor_con_cliente_falso(**kwargs):
    with patch("adapters.out.llm_anthropic.Anthropic") as mock_anthropic_cls:
        mock_client = MagicMock()
        mock_anthropic_cls.return_value = mock_client
        proveedor = ProveedorLLMAnthropic(api_key="fake-key", **kwargs)
        return proveedor, mock_client, mock_anthropic_cls


def test_usa_api_key_explicita_en_lugar_de_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    with patch("adapters.out.llm_anthropic.Anthropic") as mock_anthropic_cls:
        ProveedorLLMAnthropic(api_key="explicit-key")
        mock_anthropic_cls.assert_called_once_with(api_key="explicit-key")


def test_usa_variable_de_entorno_si_no_se_pasa_api_key(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    with patch("adapters.out.llm_anthropic.Anthropic") as mock_anthropic_cls:
        ProveedorLLMAnthropic()
        mock_anthropic_cls.assert_called_once_with(api_key="env-key")


def test_generar_respuesta_llama_al_sdk_con_los_parametros_correctos():
    proveedor, mock_client, _ = _proveedor_con_cliente_falso(modelo="claude-x")
    respuesta_falsa = MagicMock()
    respuesta_falsa.content = [_BloqueFalso("text", text="hola")]
    mock_client.messages.create.return_value = respuesta_falsa

    mensajes = [{"role": "user", "content": "hola"}]
    herramientas = [{"name": "tool1"}]

    resultado = proveedor.generar_respuesta(mensajes, herramientas=herramientas, system="system prompt")

    mock_client.messages.create.assert_called_once_with(
        model="claude-x",
        max_tokens=1024,
        system="system prompt",
        messages=mensajes,
        tools=herramientas,
    )
    assert resultado == {"content": [{"type": "text", "text": "hola"}]}


def test_generar_respuesta_valores_por_defecto_de_system_y_tools():
    proveedor, mock_client, _ = _proveedor_con_cliente_falso()
    respuesta_falsa = MagicMock()
    respuesta_falsa.content = []
    mock_client.messages.create.return_value = respuesta_falsa

    proveedor.generar_respuesta([{"role": "user", "content": "hola"}])

    _, kwargs = mock_client.messages.create.call_args
    assert kwargs["system"] == ""
    assert kwargs["tools"] == []


class _DeltaFalso:
    def __init__(self, type_, **datos):
        self.type = type_
        for k, v in datos.items():
            setattr(self, k, v)


class _EventoFalso:
    def __init__(self, type_, delta=None):
        self.type = type_
        self.delta = delta


def test_generar_respuesta_stream_emite_deltas_de_texto_y_evento_final():
    proveedor, mock_client, _ = _proveedor_con_cliente_falso(modelo="claude-x")

    eventos_sdk = [
        _EventoFalso("content_block_start"),
        _EventoFalso("content_block_delta", delta=_DeltaFalso("text_delta", text="Hola")),
        _EventoFalso("content_block_delta", delta=_DeltaFalso("text_delta", text=" mundo")),
        _EventoFalso("content_block_stop"),
    ]
    mensaje_final = MagicMock()
    mensaje_final.content = [_BloqueFalso("text", text="Hola mundo")]

    mock_stream = MagicMock()
    mock_stream.__enter__.return_value = mock_stream
    mock_stream.__exit__.return_value = False
    mock_stream.__iter__.return_value = iter(eventos_sdk)
    mock_stream.get_final_message.return_value = mensaje_final
    mock_client.messages.stream.return_value = mock_stream

    mensajes = [{"role": "user", "content": "hola"}]
    eventos = list(proveedor.generar_respuesta_stream(mensajes, system="system prompt"))

    mock_client.messages.stream.assert_called_once_with(
        model="claude-x",
        max_tokens=1024,
        system="system prompt",
        messages=mensajes,
        tools=[],
    )
    assert eventos[:-1] == [
        {"tipo": "delta_texto", "texto": "Hola"},
        {"tipo": "delta_texto", "texto": " mundo"},
    ]
    assert eventos[-1] == {
        "tipo": "final",
        "content": [{"type": "text", "text": "Hola mundo"}],
    }


def test_generar_respuesta_normaliza_bloques_tool_use():
    proveedor, mock_client, _ = _proveedor_con_cliente_falso()
    respuesta_falsa = MagicMock()
    respuesta_falsa.content = [
        _BloqueFalso("tool_use", id="call1", name="crear_reserva", input={"servicio_id": "s1"}),
    ]
    mock_client.messages.create.return_value = respuesta_falsa

    resultado = proveedor.generar_respuesta([{"role": "user", "content": "resérvame"}])

    assert resultado == {
        "content": [{
            "type": "tool_use", "id": "call1", "name": "crear_reserva",
            "input": {"servicio_id": "s1"},
        }]
    }
