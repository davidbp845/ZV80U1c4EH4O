from datetime import date, timedelta

from adapters.out.llm_mock import _RESPUESTAS_EJEMPLO, ProveedorLLMMock
from domain.ports import ProveedorLLM


def test_es_un_proveedor_llm():
    assert isinstance(ProveedorLLMMock(), ProveedorLLM)


def test_pide_disponibilidad_devuelve_tool_use():
    mock = ProveedorLLMMock()
    mensajes = [{"role": "user", "content": "¿tenéis disponibilidad mañana?"}]

    resultado = mock.generar_respuesta(mensajes)

    assert len(resultado["content"]) == 1
    bloque = resultado["content"][0]
    assert bloque["type"] == "tool_use"
    assert bloque["name"] == "comprobar_disponibilidad"
    assert bloque["id"]
    assert bloque["input"]["servicio_id"]
    assert bloque["input"]["fecha"] == (date.today() + timedelta(days=1)).isoformat()


def test_pide_hueco_tambien_dispara_tool_use():
    mock = ProveedorLLMMock()
    mensajes = [{"role": "user", "content": "¿tenéis algún hueco libre esta semana?"}]

    resultado = mock.generar_respuesta(mensajes)

    assert resultado["content"][0]["type"] == "tool_use"


def test_deteccion_de_disponibilidad_es_insensible_a_mayusculas():
    mock = ProveedorLLMMock()
    mensajes = [{"role": "user", "content": "¿DISPONIBILIDAD para el viernes?"}]

    resultado = mock.generar_respuesta(mensajes)

    assert resultado["content"][0]["type"] == "tool_use"


def test_tool_result_como_ultimo_mensaje_devuelve_texto():
    mock = ProveedorLLMMock()
    mensajes = [
        {"role": "user", "content": "resérvame algo"},
        {"role": "assistant", "content": [{"type": "tool_use", "id": "1", "name": "x", "input": {}}]},
        {"role": "user", "content": [{"type": "tool_result", "tool_use_id": "1", "content": "{}"}]},
    ]

    resultado = mock.generar_respuesta(mensajes)

    assert len(resultado["content"]) == 1
    bloque = resultado["content"][0]
    assert bloque["type"] == "text"
    assert bloque["text"]


def test_mensaje_normal_devuelve_texto_de_la_lista_de_ejemplos():
    mock = ProveedorLLMMock()
    mensajes = [{"role": "user", "content": "hola, ¿qué tal?"}]

    resultado = mock.generar_respuesta(mensajes)

    bloque = resultado["content"][0]
    assert bloque["type"] == "text"
    assert bloque["text"] in _RESPUESTAS_EJEMPLO


def test_hay_al_menos_cuatro_respuestas_variadas():
    assert len(_RESPUESTAS_EJEMPLO) >= 4
    assert len(set(_RESPUESTAS_EJEMPLO)) == len(_RESPUESTAS_EJEMPLO)


def test_sin_mensajes_no_lanza():
    resultado = ProveedorLLMMock().generar_respuesta([])
    assert resultado["content"][0]["type"] == "text"
