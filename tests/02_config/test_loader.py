from datetime import time
from textwrap import dedent

from config.loader import (
    _parse_hora, cargar_config, construir_profesionales, construir_servicios,
)


def test_parse_hora():
    assert _parse_hora("09:00") == time(9, 0)
    assert _parse_hora("18:30") == time(18, 30)


def test_cargar_config_lee_yaml(tmp_path):
    ruta = tmp_path / "business.yaml"
    ruta.write_text(dedent("""
        nombre: "Negocio de prueba"
        tono: "cercano"
        servicios: []
        profesionales: []
    """))

    config = cargar_config(str(ruta))

    assert config["nombre"] == "Negocio de prueba"
    assert config["tono"] == "cercano"


def test_construir_servicios():
    config = {
        "servicios": [
            {"id": "s1", "nombre": "Masaje", "duracion_minutos": 60, "precio": 55.0},
        ]
    }
    servicios = construir_servicios(config)

    assert len(servicios) == 1
    assert servicios[0].id == "s1"
    assert servicios[0].duracion_minutos == 60
    assert servicios[0].precio == 55.0


def test_construir_servicios_config_vacia():
    assert construir_servicios({}) == []


def test_construir_profesionales():
    config = {
        "profesionales": [
            {
                "id": "ana",
                "nombre": "Ana García",
                "servicios_ids": ["s1"],
                "horario_semanal": {"lunes": ["09:00", "18:00"]},
            }
        ]
    }
    profesionales = construir_profesionales(config)

    assert len(profesionales) == 1
    ana = profesionales[0]
    assert ana.id == "ana"
    assert ana.servicios_ids == ["s1"]
    assert ana.horario_semanal["lunes"] == (time(9, 0), time(18, 0))


def test_construir_profesionales_config_vacia():
    assert construir_profesionales({}) == []


def test_carga_config_negocio_real():
    """El config/business.yaml del repo debe seguir siendo válido y
    cargable, con los servicios y profesionales que la documentación
    (vault_negocio) da por hechos."""
    config = cargar_config("config/business.yaml")

    servicios = construir_servicios(config)
    profesionales = construir_profesionales(config)

    ids_servicios = {s.id for s in servicios}
    assert "masaje_relajante_60" in ids_servicios
    assert "masaje_descontracturante_45" in ids_servicios
    assert any(p.id == "ana" for p in profesionales)
