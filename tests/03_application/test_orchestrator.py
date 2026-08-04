from domain.ports import ProveedorLLM
from application.orchestrator import OrquestadorAgente, SesionConversacion


def _bloque_texto(texto):
    return {"type": "text", "text": texto}


def _bloque_tool_use(id_, name, input_):
    return {"type": "tool_use", "id": id_, "name": name, "input": input_}


class FakeLLM(ProveedorLLM):
    """Devuelve, en orden, las respuestas indicadas al construirlo."""

    def __init__(self, respuestas):
        self._respuestas = list(respuestas)
        self.llamadas = []

    def generar_respuesta(self, mensajes, herramientas=None, system=None):
        self.llamadas.append({"mensajes": list(mensajes), "herramientas": herramientas, "system": system})
        return self._respuestas.pop(0)


class FakeEjecutor:
    def __init__(self, resultado=None):
        self.resultado = resultado if resultado is not None else {"ok": True}
        self.llamadas = []

    def ejecutar(self, nombre_tool, entrada):
        self.llamadas.append((nombre_tool, entrada))
        return self.resultado


def test_responde_directamente_con_texto_si_no_hay_tool_use():
    llm = FakeLLM([{"content": [_bloque_texto("Hola, ¿en qué puedo ayudarte?")]}])
    orquestador = OrquestadorAgente(llm=llm, ejecutor_herramientas=FakeEjecutor(), system_prompt="system")
    sesion = SesionConversacion(canal="web", usuario_id="u1")

    respuesta = orquestador.responder(sesion, "hola")

    assert respuesta == "Hola, ¿en qué puedo ayudarte?"
    assert sesion.historial[0] == {"role": "user", "content": "hola"}
    assert llm.llamadas[0]["system"] == "system"


def test_ejecuta_tool_y_responde_con_el_siguiente_texto():
    llm = FakeLLM([
        {"content": [_bloque_tool_use("call1", "consultar_conocimiento_negocio", {"consulta": "precios"})]},
        {"content": [_bloque_texto("El masaje cuesta 55€.")]},
    ])
    ejecutor = FakeEjecutor(resultado={"fragmentos": ["55€"]})
    orquestador = OrquestadorAgente(llm=llm, ejecutor_herramientas=ejecutor, system_prompt="system")
    sesion = SesionConversacion(canal="web", usuario_id="u1")

    respuesta = orquestador.responder(sesion, "¿cuánto cuesta el masaje?")

    assert respuesta == "El masaje cuesta 55€."
    assert ejecutor.llamadas == [("consultar_conocimiento_negocio", {"consulta": "precios"})]

    mensajes_tool_result = sesion.historial[2]["content"]
    assert mensajes_tool_result[0]["type"] == "tool_result"
    assert mensajes_tool_result[0]["tool_use_id"] == "call1"
    assert "55" in mensajes_tool_result[0]["content"]


def test_concatena_varios_bloques_de_texto():
    llm = FakeLLM([{"content": [_bloque_texto("Primera parte."), _bloque_texto("Segunda parte.")]}])
    orquestador = OrquestadorAgente(llm=llm, ejecutor_herramientas=FakeEjecutor(), system_prompt="system")
    sesion = SesionConversacion(canal="web", usuario_id="u1")

    respuesta = orquestador.responder(sesion, "hola")

    assert respuesta == "Primera parte.\nSegunda parte."


def test_da_mensaje_de_fallback_tras_agotar_iteraciones():
    respuestas = [
        {"content": [_bloque_tool_use(f"call{i}", "comprobar_disponibilidad", {})]}
        for i in range(4)
    ]
    llm = FakeLLM(respuestas)
    orquestador = OrquestadorAgente(
        llm=llm, ejecutor_herramientas=FakeEjecutor(), system_prompt="system",
        max_iteraciones_tool=4,
    )
    sesion = SesionConversacion(canal="web", usuario_id="u1")

    respuesta = orquestador.responder(sesion, "resérvame algo")

    assert "no he podido completar" in respuesta
    assert len(llm.llamadas) == 4


def test_historial_se_mantiene_entre_llamadas_a_responder():
    llm = FakeLLM([
        {"content": [_bloque_texto("Respuesta 1")]},
        {"content": [_bloque_texto("Respuesta 2")]},
    ])
    orquestador = OrquestadorAgente(llm=llm, ejecutor_herramientas=FakeEjecutor(), system_prompt="system")
    sesion = SesionConversacion(canal="web", usuario_id="u1")

    orquestador.responder(sesion, "primer mensaje")
    orquestador.responder(sesion, "segundo mensaje")

    roles_y_contenido = [m["content"] for m in sesion.historial if m["role"] == "user"]
    assert roles_y_contenido[0] == "primer mensaje"
    assert roles_y_contenido[1] == "segundo mensaje"
