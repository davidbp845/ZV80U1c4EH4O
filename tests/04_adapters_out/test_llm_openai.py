from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from adapters.out.llm_openai import ProveedorLLMOpenAI


def _proveedor_con_cliente_falso(**kwargs):
    with patch("adapters.out.llm_openai.OpenAI") as mock_cliente_cls:
        mock_cliente = MagicMock()
        mock_cliente_cls.return_value = mock_cliente
        proveedor = ProveedorLLMOpenAI(api_key="fake-key", **kwargs)
        return proveedor, mock_cliente, mock_cliente_cls


def test_usa_api_key_explicita_en_lugar_de_variable_de_entorno(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    with patch("adapters.out.llm_openai.OpenAI") as mock_cliente_cls:
        ProveedorLLMOpenAI(api_key="explicit-key")
        mock_cliente_cls.assert_called_once_with(api_key="explicit-key")


def test_usa_variable_de_entorno_si_no_se_pasa_api_key(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "env-key")
    with patch("adapters.out.llm_openai.OpenAI") as mock_cliente_cls:
        ProveedorLLMOpenAI()
        mock_cliente_cls.assert_called_once_with(api_key="env-key")


def test_traducir_herramientas_mapea_input_schema_a_parameters():
    herramientas = [{
        "name": "comprobar_disponibilidad",
        "description": "Consulta huecos libres.",
        "input_schema": {
            "type": "object",
            "properties": {"servicio_id": {"type": "string"}},
            "required": ["servicio_id"],
        },
    }]

    traducidas = ProveedorLLMOpenAI._traducir_herramientas(herramientas)

    assert traducidas == [{
        "type": "function",
        "function": {
            "name": "comprobar_disponibilidad",
            "description": "Consulta huecos libres.",
            "parameters": herramientas[0]["input_schema"],
        },
    }]


def test_traducir_historial_turno_de_usuario_pasa_igual():
    mensajes = [{"role": "user", "content": "hola"}]

    traducidos = ProveedorLLMOpenAI._traducir_historial(mensajes, system=None)

    assert traducidos == [{"role": "user", "content": "hola"}]


def test_traducir_historial_incluye_mensaje_de_sistema_si_se_pasa():
    traducidos = ProveedorLLMOpenAI._traducir_historial([], system="prompt del sistema")
    assert traducidos[0] == {"role": "system", "content": "prompt del sistema"}


def test_traducir_historial_turno_de_asistente_con_tool_use():
    mensajes = [{
        "role": "assistant",
        "content": [
            {"type": "text", "text": "Voy a consultar."},
            {"type": "tool_use", "id": "call1", "name": "consultar_conocimiento_negocio",
             "input": {"consulta": "precios"}},
        ],
    }]

    traducidos = ProveedorLLMOpenAI._traducir_historial(mensajes, system=None)

    assert traducidos == [{
        "role": "assistant",
        "content": "Voy a consultar.",
        "tool_calls": [{
            "id": "call1",
            "type": "function",
            "function": {
                "name": "consultar_conocimiento_negocio",
                "arguments": '{"consulta": "precios"}',
            },
        }],
    }]


def test_traducir_historial_turno_de_asistente_solo_texto():
    mensajes = [{"role": "assistant", "content": [{"type": "text", "text": "Hola."}]}]

    traducidos = ProveedorLLMOpenAI._traducir_historial(mensajes, system=None)

    assert traducidos == [{"role": "assistant", "content": "Hola."}]


def test_traducir_historial_expande_tool_results_en_mensajes_tool_separados():
    mensajes = [{
        "role": "user",
        "content": [
            {"type": "tool_result", "tool_use_id": "call1", "content": "resultado 1"},
            {"type": "tool_result", "tool_use_id": "call2", "content": "resultado 2"},
        ],
    }]

    traducidos = ProveedorLLMOpenAI._traducir_historial(mensajes, system=None)

    assert traducidos == [
        {"role": "tool", "tool_call_id": "call1", "content": "resultado 1"},
        {"role": "tool", "tool_call_id": "call2", "content": "resultado 2"},
    ]


def test_generar_respuesta_normaliza_texto_y_tool_calls():
    proveedor, mock_cliente, _ = _proveedor_con_cliente_falso(modelo="gpt-x")

    mensaje_falso = SimpleNamespace(
        content="hola",
        tool_calls=[
            SimpleNamespace(
                id="call1",
                function=SimpleNamespace(name="crear_reserva", arguments='{"servicio_id": "s1"}'),
            ),
        ],
    )
    mock_cliente.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=mensaje_falso)]
    )

    resultado = proveedor.generar_respuesta(
        [{"role": "user", "content": "resérvame"}],
        herramientas=[{"name": "crear_reserva", "description": "d", "input_schema": {}}],
        system="system prompt",
    )

    assert resultado == {
        "content": [
            {"type": "text", "text": "hola"},
            {"type": "tool_use", "id": "call1", "name": "crear_reserva", "input": {"servicio_id": "s1"}},
        ]
    }
    _, kwargs = mock_cliente.chat.completions.create.call_args
    assert kwargs["model"] == "gpt-x"
    assert kwargs["messages"][0] == {"role": "system", "content": "system prompt"}
    assert kwargs["tools"][0]["function"]["name"] == "crear_reserva"
    assert kwargs["temperature"] == 0


def test_generar_respuesta_sin_texto_omite_bloque_de_texto():
    proveedor, mock_cliente, _ = _proveedor_con_cliente_falso()

    mensaje_falso = SimpleNamespace(content=None, tool_calls=None)
    mock_cliente.chat.completions.create.return_value = SimpleNamespace(
        choices=[SimpleNamespace(message=mensaje_falso)]
    )

    resultado = proveedor.generar_respuesta([{"role": "user", "content": "hola"}])

    assert resultado == {"content": []}


def test_generar_respuesta_stream_emite_deltas_y_final_de_texto():
    proveedor, mock_cliente, _ = _proveedor_con_cliente_falso()

    chunks = [
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content="Hola", tool_calls=None))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=" mundo", tool_calls=None))]),
    ]
    mock_cliente.chat.completions.create.return_value = iter(chunks)

    eventos_recibidos = list(proveedor.generar_respuesta_stream([{"role": "user", "content": "hola"}]))

    assert eventos_recibidos[:-1] == [
        {"tipo": "delta_texto", "texto": "Hola"},
        {"tipo": "delta_texto", "texto": " mundo"},
    ]
    assert eventos_recibidos[-1] == {
        "tipo": "final",
        "content": [{"type": "text", "text": "Hola mundo"}],
    }
    _, kwargs = mock_cliente.chat.completions.create.call_args
    assert kwargs["temperature"] == 0
    assert kwargs["stream"] is True


def test_generar_respuesta_stream_acumula_tool_calls_y_emite_final_tool_use():
    proveedor, mock_cliente, _ = _proveedor_con_cliente_falso()

    chunks = [
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(
            content=None,
            tool_calls=[SimpleNamespace(
                index=0, id="call1",
                function=SimpleNamespace(name="comprobar_disponibilidad", arguments=""),
            )],
        ))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(
            content=None,
            tool_calls=[SimpleNamespace(
                index=0, id=None,
                function=SimpleNamespace(name=None, arguments='{"servicio_id"'),
            )],
        ))]),
        SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(
            content=None,
            tool_calls=[SimpleNamespace(
                index=0, id=None,
                function=SimpleNamespace(name=None, arguments=': "s1"}'),
            )],
        ))]),
    ]
    mock_cliente.chat.completions.create.return_value = iter(chunks)

    eventos_recibidos = list(proveedor.generar_respuesta_stream([{"role": "user", "content": "hola"}]))

    assert eventos_recibidos == [{
        "tipo": "final",
        "content": [{
            "type": "tool_use", "id": "call1", "name": "comprobar_disponibilidad",
            "input": {"servicio_id": "s1"},
        }],
    }]
