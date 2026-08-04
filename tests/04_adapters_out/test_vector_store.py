"""No golpea la red ni descarga modelos de embeddings reales: se
mockean chromadb.PersistentClient y la función de embeddings, ya que
lo único que le corresponde probar a este adaptador es que traduce
correctamente el puerto RepositorioConocimiento a llamadas de
chromadb."""
from unittest.mock import MagicMock, patch

from adapters.out.vector_store import RepositorioConocimientoChroma


def _construir_con_mocks(ruta_datos="./chroma_test", **kwargs):
    with patch("adapters.out.vector_store.chromadb.PersistentClient") as mock_client_cls, \
         patch("adapters.out.vector_store.embedding_functions.DefaultEmbeddingFunction") as mock_embed_cls:
        mock_client = MagicMock()
        mock_coleccion = MagicMock()
        mock_client.get_or_create_collection.return_value = mock_coleccion
        mock_client_cls.return_value = mock_client

        repo = RepositorioConocimientoChroma(ruta_datos=ruta_datos, **kwargs)
        return repo, mock_client, mock_coleccion, mock_client_cls, mock_embed_cls


def test_inicializa_cliente_persistente_en_la_ruta_indicada():
    repo, mock_client, mock_coleccion, mock_client_cls, _ = _construir_con_mocks(
        ruta_datos="/tmp/chroma_test"
    )
    mock_client_cls.assert_called_once_with(path="/tmp/chroma_test")
    mock_client.get_or_create_collection.assert_called_once()
    _, kwargs = mock_client.get_or_create_collection.call_args
    assert kwargs["name"] == "conocimiento_negocio"


def test_usa_chroma_path_del_entorno_si_no_se_indica_ruta(monkeypatch):
    monkeypatch.setenv("CHROMA_PATH", "/env/chroma")
    with patch("adapters.out.vector_store.chromadb.PersistentClient") as mock_client_cls, \
         patch("adapters.out.vector_store.embedding_functions.DefaultEmbeddingFunction"):
        mock_client_cls.return_value.get_or_create_collection.return_value = MagicMock()
        RepositorioConocimientoChroma()
        mock_client_cls.assert_called_once_with(path="/env/chroma")


def test_indexar_fragmentos_llama_a_upsert_con_ids_documentos_y_metadatos():
    repo, _, mock_coleccion, _, _ = _construir_con_mocks()

    repo.indexar_fragmentos([
        {"id": "f1", "texto": "contenido 1", "metadata": {"fuente": "a.md"}},
        {"id": "f2", "texto": "contenido 2"},
    ])

    mock_coleccion.upsert.assert_called_once_with(
        ids=["f1", "f2"],
        documents=["contenido 1", "contenido 2"],
        metadatas=[{"fuente": "a.md"}, {}],
    )


def test_indexar_fragmentos_lista_vacia_no_llama_a_upsert():
    repo, _, mock_coleccion, _, _ = _construir_con_mocks()

    repo.indexar_fragmentos([])

    mock_coleccion.upsert.assert_not_called()


def test_buscar_devuelve_los_documentos_de_la_query():
    repo, _, mock_coleccion, _, _ = _construir_con_mocks()
    mock_coleccion.query.return_value = {"documents": [["frag1", "frag2"]]}

    resultado = repo.buscar("¿cuáles son los precios?", top_k=3)

    mock_coleccion.query.assert_called_once_with(
        query_texts=["¿cuáles son los precios?"], n_results=3
    )
    assert resultado == ["frag1", "frag2"]


def test_buscar_sin_documentos_devuelve_lista_vacia():
    repo, _, mock_coleccion, _, _ = _construir_con_mocks()
    mock_coleccion.query.return_value = {"documents": []}

    assert repo.buscar("consulta") == []
