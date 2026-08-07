from datetime import date

from application.prompts import construir_system_prompt, formatear_fecha_es


def test_usa_valores_por_defecto_si_faltan_en_config():
    prompt = construir_system_prompt({})
    assert "el negocio" in prompt
    assert "cercano y profesional" in prompt


def test_incluye_nombre_y_tono_del_negocio():
    prompt = construir_system_prompt({"nombre": "Centro Serenidad", "tono": "formal"})
    assert "Centro Serenidad" in prompt
    assert "formal" in prompt


def test_incluye_instrucciones_extra():
    prompt = construir_system_prompt({
        "nombre": "Centro Serenidad",
        "instrucciones_extra": "Deriva dolencias graves a un profesional sanitario.",
    })
    assert "Deriva dolencias graves a un profesional sanitario." in prompt


def test_incluye_instrucciones_comerciales():
    prompt = construir_system_prompt({
        "nombre": "Centro Serenidad",
        "instrucciones_comerciales": "No te despidas nunca de un cliente insatisfecho.",
    })
    assert "No te despidas nunca de un cliente insatisfecho." in prompt


def test_prompt_no_tiene_espacios_sobrantes_al_final():
    prompt = construir_system_prompt({"nombre": "X"})
    assert prompt == prompt.strip()


def test_incluye_catalogo_de_servicios_y_profesionales_con_ids_exactos():
    prompt = construir_system_prompt({
        "nombre": "Centro Serenidad",
        "servicios": [
            {"id": "masaje_relajante_60", "nombre": "Masaje relajante 60 min",
             "duracion_minutos": 60, "precio": 55.0},
        ],
        "profesionales": [
            {"id": "ana", "nombre": "Ana García", "servicios_ids": ["masaje_relajante_60"]},
        ],
    })
    assert "masaje_relajante_60" in prompt
    assert "Masaje relajante 60 min" in prompt
    assert "ana" in prompt
    assert "Ana García" in prompt


def test_sin_servicios_ni_profesionales_no_incluye_catalogo():
    prompt = construir_system_prompt({"nombre": "Centro Serenidad"})
    assert "Catálogo de servicios" not in prompt


def test_formatear_fecha_es_viernes():
    assert formatear_fecha_es(date(2026, 8, 7)) == "viernes 7 de agosto de 2026"


def test_formatear_fecha_es_lunes():
    assert formatear_fecha_es(date(2026, 8, 10)) == "lunes 10 de agosto de 2026"


def test_formatear_fecha_es_no_depende_del_locale_del_sistema():
    # Fechas con meses/días distintos, para pillar off-by-one en los
    # índices de _DIAS_SEMANA_ES/_MESES_ES.
    assert formatear_fecha_es(date(2026, 1, 1)) == "jueves 1 de enero de 2026"
    assert formatear_fecha_es(date(2026, 12, 31)) == "jueves 31 de diciembre de 2026"
