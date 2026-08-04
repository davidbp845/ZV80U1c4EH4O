"""main.py es el composition root: aquí solo verificamos que
construir_sistema() conecta correctamente adaptadores, casos de uso y
orquestador. Se mockean los adaptadores que hablan con servicios
externos reales (Anthropic, Chroma) para que el test sea rápido y no
dependa de red ni de credenciales."""
from unittest.mock import MagicMock, patch

from application.orchestrator import OrquestadorAgente


def test_construir_sistema_conecta_las_piezas():
    with patch("main.ProveedorLLMAnthropic") as mock_llm_cls, \
         patch("main.RepositorioConocimientoChroma") as mock_chroma_cls:
        mock_llm_cls.return_value = MagicMock()
        mock_chroma_cls.return_value = MagicMock()

        import main
        orquestador, config = main.construir_sistema("config/business.yaml")

    assert isinstance(orquestador, OrquestadorAgente)
    assert config["nombre"] == "Centro de Masajes Serenity"

    herramientas_esperadas = {
        "comprobar_disponibilidad", "crear_reserva", "cancelar_reserva",
        "registrar_pedido", "consultar_conocimiento",
    }
    assert set(orquestador._ejecutor._casos.keys()) == herramientas_esperadas
    assert "Centro de Masajes Serenity" in orquestador._system_prompt


def test_construir_sistema_carga_servicios_y_profesionales_del_yaml():
    with patch("main.ProveedorLLMAnthropic") as mock_llm_cls, \
         patch("main.RepositorioConocimientoChroma") as mock_chroma_cls:
        mock_llm_cls.return_value = MagicMock()
        mock_chroma_cls.return_value = MagicMock()

        import main
        orquestador, _ = main.construir_sistema("config/business.yaml")

    disponibilidad = orquestador._ejecutor._casos["comprobar_disponibilidad"]
    servicios = disponibilidad._servicios.listar()
    ids_servicios = {s.id for s in servicios}

    assert "masaje_relajante_60" in ids_servicios
    assert "masaje_descontracturante_45" in ids_servicios


def test_construir_sistema_usa_llm_real_por_defecto(monkeypatch):
    monkeypatch.delenv("USE_MOCK_LLM", raising=False)
    with patch("main.ProveedorLLMAnthropic") as mock_llm_cls, \
         patch("main.RepositorioConocimientoChroma") as mock_chroma_cls:
        mock_llm_cls.return_value = MagicMock()
        mock_chroma_cls.return_value = MagicMock()

        import main
        orquestador, _ = main.construir_sistema("config/business.yaml")

    assert orquestador._llm is mock_llm_cls.return_value


def test_construir_sistema_usa_llm_mock_si_use_mock_llm_es_true(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "true")
    with patch("main.RepositorioConocimientoChroma") as mock_chroma_cls:
        mock_chroma_cls.return_value = MagicMock()

        import main
        orquestador, _ = main.construir_sistema("config/business.yaml")

    from adapters.out.llm_mock import ProveedorLLMMock
    assert isinstance(orquestador._llm, ProveedorLLMMock)


def test_construir_sistema_usa_llm_real_si_use_mock_llm_es_false(monkeypatch):
    monkeypatch.setenv("USE_MOCK_LLM", "false")
    with patch("main.ProveedorLLMAnthropic") as mock_llm_cls, \
         patch("main.RepositorioConocimientoChroma") as mock_chroma_cls:
        mock_llm_cls.return_value = MagicMock()
        mock_chroma_cls.return_value = MagicMock()

        import main
        orquestador, _ = main.construir_sistema("config/business.yaml")

    assert orquestador._llm is mock_llm_cls.return_value
