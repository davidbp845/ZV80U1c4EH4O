from datetime import datetime


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
