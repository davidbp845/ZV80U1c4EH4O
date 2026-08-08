from adapters.out.repositorio_sesiones_memoria import RepositorioSesionesMemoria
from application.orchestrator import SesionConversacion


def test_obtener_devuelve_none_si_no_existe():
    repo = RepositorioSesionesMemoria()
    assert repo.obtener("web", "u1") is None


def test_guardar_y_obtener_devuelve_la_misma_sesion():
    repo = RepositorioSesionesMemoria()
    sesion = SesionConversacion(canal="web", usuario_id="u1", historial=[{"role": "user", "content": "hola"}])

    repo.guardar(sesion)

    assert repo.obtener("web", "u1") is sesion


def test_mismo_usuario_id_en_canales_distintos_no_colisiona():
    repo = RepositorioSesionesMemoria()
    sesion_web = SesionConversacion(canal="web", usuario_id="u1", historial=[{"role": "user", "content": "web"}])
    sesion_telegram = SesionConversacion(
        canal="telegram", usuario_id="u1", historial=[{"role": "user", "content": "telegram"}]
    )

    repo.guardar(sesion_web)
    repo.guardar(sesion_telegram)

    assert repo.obtener("web", "u1") is sesion_web
    assert repo.obtener("telegram", "u1") is sesion_telegram
