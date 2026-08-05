"""adapters/in_/fastapi_app.py define `app` y `_sesiones` a nivel de
módulo, y crear_router() añade rutas sobre ese mismo `app` cada vez
que se llama. Para que cada test tenga rutas y sesiones limpias (y no
dependa del orden de ejecución), recargamos el módulo en cada test en
lugar de reutilizar la instancia compartida."""
import importlib

import pytest
from fastapi.testclient import TestClient


class FakeOrquestador:
    def __init__(self, respuesta="Hola, ¿en qué puedo ayudarte?", fuentes=None, eventos_stream=None):
        self.respuesta = respuesta
        self.fuentes = fuentes or []
        self.eventos_stream = eventos_stream
        self.llamadas = []

    def responder(self, sesion, mensaje):
        self.llamadas.append((sesion.usuario_id, mensaje))
        return self.respuesta

    def responder_stream(self, sesion, mensaje):
        self.llamadas.append((sesion.usuario_id, mensaje))
        if self.eventos_stream is not None:
            yield from self.eventos_stream
            return
        yield {"tipo": "delta", "texto": self.respuesta}
        yield {"tipo": "done", "respuesta": self.respuesta, "fuentes": self.fuentes}


@pytest.fixture
def modulo():
    import adapters.in_.fastapi_app as fastapi_app
    importlib.reload(fastapi_app)
    return fastapi_app


@pytest.fixture
def cliente(modulo):
    orquestador = FakeOrquestador()
    app = modulo.crear_router(orquestador)
    return TestClient(app), orquestador, modulo


def test_health(cliente):
    client, _, _ = cliente
    respuesta = client.get("/health")
    assert respuesta.status_code == 200
    assert respuesta.json() == {"status": "ok"}


def test_chat_devuelve_la_respuesta_del_orquestador(cliente):
    client, orquestador, _ = cliente
    respuesta = client.post("/chat", json={"usuario_id": "u1", "mensaje": "hola"})

    assert respuesta.status_code == 200
    assert respuesta.json() == {"respuesta": orquestador.respuesta}
    assert orquestador.llamadas == [("u1", "hola")]


def test_chat_reutiliza_la_sesion_del_mismo_usuario(cliente):
    client, orquestador, modulo = cliente

    client.post("/chat", json={"usuario_id": "u2", "mensaje": "primero"})
    client.post("/chat", json={"usuario_id": "u2", "mensaje": "segundo"})

    sesion = modulo._sesiones["u2"]
    assert sesion.canal == "web"
    assert [m for _, m in orquestador.llamadas] == ["primero", "segundo"]


def test_chat_valida_payload_incompleto(cliente):
    client, _, _ = cliente
    respuesta = client.post("/chat", json={"usuario_id": "u3"})
    assert respuesta.status_code == 422


def test_chat_stream_emite_frames_sse_de_delta_fuentes_y_done(cliente):
    client, orquestador, _ = cliente
    orquestador.respuesta = "Hola!"
    orquestador.fuentes = [{"fuente": "servicios.md", "categoria": "servicios"}]

    respuesta = client.post("/chat/stream", json={"usuario_id": "u1", "mensaje": "hola"})

    assert respuesta.status_code == 200
    assert respuesta.headers["content-type"].startswith("text/event-stream")
    cuerpo = respuesta.text
    assert "event: delta" in cuerpo
    assert '"texto": "Hola!"' in cuerpo
    assert "event: fuentes" in cuerpo
    assert "servicios.md" in cuerpo
    assert "event: done" in cuerpo
    assert orquestador.llamadas == [("u1", "hola")]


def test_chat_stream_emite_evento_error_si_el_orquestador_lanza(cliente):
    client, orquestador, _ = cliente

    def generador_roto(sesion, mensaje):
        yield {"tipo": "delta", "texto": "empiezo..."}
        raise RuntimeError("fallo de LLM")

    orquestador.responder_stream = generador_roto

    respuesta = client.post("/chat/stream", json={"usuario_id": "u1", "mensaje": "hola"})

    assert respuesta.status_code == 200
    assert "event: error" in respuesta.text
    assert "fallo de LLM" in respuesta.text


@pytest.mark.parametrize("origen", ["http://localhost:5173", "http://localhost:3000", "http://localhost:4321"])
def test_cors_permite_origenes_de_dev_habituales(cliente, origen):
    client, _, _ = cliente
    respuesta = client.options(
        "/chat",
        headers={
            "Origin": origen,
            "Access-Control-Request-Method": "POST",
        },
    )
    assert respuesta.headers["access-control-allow-origin"] == origen


def test_cors_rechaza_origen_no_autorizado(cliente):
    client, _, _ = cliente
    respuesta = client.options(
        "/chat",
        headers={
            "Origin": "http://evil.example",
            "Access-Control-Request-Method": "POST",
        },
    )
    assert "access-control-allow-origin" not in respuesta.headers
