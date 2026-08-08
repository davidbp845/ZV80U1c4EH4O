from datetime import datetime

from domain.entities import EstadoPedido
from domain.exceptions import (
    DominioError,
    PedidoNoExiste,
    ProfesionalNoDisponible,
    ServicioNoExiste,
    TransicionEstadoInvalida,
)


def test_servicio_no_existe_es_dominio_error():
    exc = ServicioNoExiste("masaje_x")
    assert isinstance(exc, DominioError)
    assert exc.servicio_id == "masaje_x"
    assert "masaje_x" in str(exc)


def test_profesional_no_disponible_es_dominio_error():
    inicio = datetime(2026, 8, 3, 9, 0)
    exc = ProfesionalNoDisponible("ana", inicio)
    assert isinstance(exc, DominioError)
    assert exc.profesional_id == "ana"
    assert exc.inicio == inicio
    assert "ana" in str(exc)


def test_dominio_error_es_exception():
    assert issubclass(DominioError, Exception)


def test_pedido_no_existe_es_dominio_error():
    exc = PedidoNoExiste("pedido-x")
    assert isinstance(exc, DominioError)
    assert exc.pedido_id == "pedido-x"
    assert "pedido-x" in str(exc)


def test_transicion_estado_invalida_es_dominio_error():
    exc = TransicionEstadoInvalida(EstadoPedido.ENTREGADO, EstadoPedido.RECIBIDO)
    assert isinstance(exc, DominioError)
    assert exc.estado_actual == EstadoPedido.ENTREGADO
    assert exc.estado_nuevo == EstadoPedido.RECIBIDO
