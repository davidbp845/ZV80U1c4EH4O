from application.prompts import construir_system_prompt


def test_usa_valores_por_defecto_si_faltan_en_config():
    prompt = construir_system_prompt({})
    assert "el negocio" in prompt
    assert "cercano y profesional" in prompt


def test_incluye_nombre_y_tono_del_negocio():
    prompt = construir_system_prompt({"nombre": "Centro Serenity", "tono": "formal"})
    assert "Centro Serenity" in prompt
    assert "formal" in prompt


def test_incluye_instrucciones_extra():
    prompt = construir_system_prompt({
        "nombre": "Centro Serenity",
        "instrucciones_extra": "Deriva dolencias graves a un profesional sanitario.",
    })
    assert "Deriva dolencias graves a un profesional sanitario." in prompt


def test_prompt_no_tiene_espacios_sobrantes_al_final():
    prompt = construir_system_prompt({"nombre": "X"})
    assert prompt == prompt.strip()
