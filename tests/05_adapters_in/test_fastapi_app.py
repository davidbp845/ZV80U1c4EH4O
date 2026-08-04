"""adapters/in_/fastapi_app.py define `app` y `_sesiones` a nivel de
módulo, y crear_router() añade rutas sobre ese mismo `app` cada vez
que se llama. Para que cada test tenga rutas y sesiones limpias (y no
dependa del orden de ejecución), recargamos el módulo en cada test en
lugar de reutilizar la instancia compartida."""
import importlib

import pytest
from fastapi.testclient import TestClient


class FakeOrquestador:
    def __init__(self, respuesta="Hola, ¿en qué puedo ayudarte?"):
        self.respuesta = respuesta
        self.llamadas = []

    def responder(self, sesion, mensaje):
        self.llamadas.append((sesion.usuario_id, mensaje))
        return self.respuesta


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
