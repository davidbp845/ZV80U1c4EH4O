from unittest.mock import MagicMock, patch

from adapters.out.obsidian_ingest import main, procesar_vault, trocear_texto


def test_trocear_texto_un_solo_parrafo_corto():
    assert trocear_texto("Hola mundo.") == ["Hola mundo."]


def test_trocear_texto_respeta_tamano_maximo():
    parrafos = ["a" * 5, "b" * 5, "c" * 5]
    texto = "\n\n".join(parrafos)

    fragmentos = trocear_texto(texto, tamano=8, solape=2)

    # Cada párrafo (5 chars) no cabe junto a otro en un tamaño de 8,
    # así que cada uno debería acabar en un fragmento distinto.
    assert len(fragmentos) == 3
    assert all(len(f) <= 8 + 2 + 2 for f in fragmentos)  # margen por el solape


def test_trocear_texto_agrupa_parrafos_que_caben_juntos():
    texto = "corto1\n\ncorto2"
    fragmentos = trocear_texto(texto, tamano=100, solape=10)
    assert fragmentos == ["corto1\n\ncorto2"]


def test_trocear_texto_vacio():
    assert trocear_texto("   ") == []


def test_procesar_vault_extrae_fragmentos_con_metadata(tmp_path):
    (tmp_path / "precios.md").write_text(
        "---\ncategoria: precios\n---\n\nEl masaje cuesta 55 euros.\n"
    )
    subdir = tmp_path / "sub"
    subdir.mkdir()
    (subdir / "horarios.md").write_text("Abrimos de 9 a 18.")

    fragmentos = procesar_vault(str(tmp_path))

    assert len(fragmentos) == 2
    fuentes = {f["metadata"]["fuente"] for f in fragmentos}
    assert fuentes == {"precios.md", "sub/horarios.md"}

    precios = next(f for f in fragmentos if f["metadata"]["fuente"] == "precios.md")
    assert precios["metadata"]["categoria"] == "precios"
    assert "55 euros" in precios["texto"]
    assert precios["id"]  # se genera un hash no vacío


def test_procesar_vault_ids_son_deterministas(tmp_path):
    (tmp_path / "a.md").write_text("contenido")

    fragmentos1 = procesar_vault(str(tmp_path))
    fragmentos2 = procesar_vault(str(tmp_path))

    assert fragmentos1[0]["id"] == fragmentos2[0]["id"]


def test_procesar_vault_directorio_vacio(tmp_path):
    assert procesar_vault(str(tmp_path)) == []


def test_main_indexa_los_fragmentos_del_vault(tmp_path, monkeypatch, capsys):
    (tmp_path / "faq.md").write_text("Pregunta frecuente de ejemplo.")

    monkeypatch.setattr(
        "sys.argv",
        ["obsidian_ingest", "--vault", str(tmp_path), "--chroma-path", str(tmp_path / "chroma")],
    )

    mock_store = MagicMock()
    with patch("adapters.out.obsidian_ingest.RepositorioConocimientoChroma", return_value=mock_store) as mock_cls:
        main()

    mock_cls.assert_called_once_with(ruta_datos=str(tmp_path / "chroma"))
    mock_store.indexar_fragmentos.assert_called_once()
    fragmentos_pasados = mock_store.indexar_fragmentos.call_args[0][0]
    assert len(fragmentos_pasados) == 1

    salida = capsys.readouterr().out
    assert "Encontrados 1 fragmentos" in salida
    assert "Ingesta completada." in salida
