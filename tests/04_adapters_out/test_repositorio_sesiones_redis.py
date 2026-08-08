"""No golpea una instancia Redis real: se mockea redis.Redis, ya que
lo único que le corresponde probar a este adaptador es que traduce
correctamente el puerto RepositorioSesiones (serialización JSON del
historial, construcción de la clave) a llamadas de get/set."""
import json
from unittest.mock import MagicMock, patch

from adapters.out.repositorio_sesiones_redis import RepositorioSesionesRedis
from application.orchestrator import SesionConversacion


def _construir_con_cliente_falso():
    mock_cliente = MagicMock()
    repo = RepositorioSesionesRedis("redis://localhost:6379", cliente=mock_cliente)
    return repo, mock_cliente


def test_usa_redis_from_url_si_no_se_pasa_cliente():
    with patch("adapters.out.repositorio_sesiones_redis.Redis") as mock_redis_cls:
        RepositorioSesionesRedis("redis://localhost:6379")
        mock_redis_cls.from_url.assert_called_once_with(
            "redis://localhost:6379", decode_responses=True
        )


def test_obtener_devuelve_none_si_no_existe():
    repo, mock_cliente = _construir_con_cliente_falso()
    mock_cliente.get.return_value = None

    assert repo.obtener("web", "u1") is None
    mock_cliente.get.assert_called_once_with("sesion:web:u1")


def test_obtener_deserializa_el_historial_guardado():
    repo, mock_cliente = _construir_con_cliente_falso()
    mock_cliente.get.return_value = json.dumps([{"role": "user", "content": "hola"}])

    sesion = repo.obtener("web", "u1")

    assert sesion == SesionConversacion(
        canal="web", usuario_id="u1", historial=[{"role": "user", "content": "hola"}]
    )


def test_guardar_serializa_el_historial_como_json():
    repo, mock_cliente = _construir_con_cliente_falso()
    sesion = SesionConversacion(canal="telegram", usuario_id="u2", historial=[{"role": "user", "content": "hola"}])

    repo.guardar(sesion)

    mock_cliente.set.assert_called_once_with(
        "sesion:telegram:u2", json.dumps([{"role": "user", "content": "hola"}])
    )
