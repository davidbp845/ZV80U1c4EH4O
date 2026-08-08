from datetime import datetime
from uuid import UUID

from .entities import EstadoPedido


class DominioError(Exception):
    """Excepción base de dominio."""


class ServicioNoExiste(DominioError):
    def __init__(self, servicio_id: str) -> None:
        super().__init__(f"El servicio '{servicio_id}' no existe.")
        self.servicio_id = servicio_id


class ProfesionalNoDisponible(DominioError):
    def __init__(self, profesional_id: str, inicio: datetime) -> None:
        super().__init__(
            f"El profesional '{profesional_id}' no tiene hueco a las {inicio}."
        )
        self.profesional_id = profesional_id
        self.inicio = inicio


class PedidoNoExiste(DominioError):
    def __init__(self, pedido_id: UUID) -> None:
        super().__init__(f"El pedido '{pedido_id}' no existe.")
        self.pedido_id = pedido_id


class TransicionEstadoInvalida(DominioError):
    def __init__(self, estado_actual: EstadoPedido, estado_nuevo: EstadoPedido) -> None:
        super().__init__(
            f"No se puede pasar un pedido de '{estado_actual}' a '{estado_nuevo}'."
        )
        self.estado_actual = estado_actual
        self.estado_nuevo = estado_nuevo
