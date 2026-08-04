"""
Pipeline de ingesta: recorre el vault de Obsidian (ficheros .md con
frontmatter YAML opcional), los trocea y los indexa en el vector
store. Este mismo vault puede servir directamente de contenido para
la web (renderizando el markdown), así que es la única fuente de
verdad documental del negocio.

Uso:
    python -m adapters.out.obsidian_ingest --vault ./vault_negocio
Ideal ejecutarlo como git hook post-commit o watcher de filesystem
sobre la carpeta del vault, para que quede siempre sincronizado.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import frontmatter  # python-frontmatter

from .vector_store import RepositorioConocimientoChroma

TAMANO_CHUNK = 800       # caracteres aprox. por fragmento
SOLAPE_CHUNK = 100        # caracteres de solape entre fragmentos consecutivos


def trocear_texto(texto: str, tamano: int = TAMANO_CHUNK, solape: int = SOLAPE_CHUNK) -> list[str]:
    """Chunking simple por párrafos, respetando límites de tamaño.
    Para necesidades más finas (splitting semántico) sustituir por
    langchain.text_splitter o similar sin tocar el resto del pipeline."""
    parrafos = re.split(r"\n\s*\n", texto.strip())
    fragmentos: list[str] = []
    actual = ""

    for parrafo in parrafos:
        if len(actual) + len(parrafo) <= tamano:
            actual += ("\n\n" if actual else "") + parrafo
        else:
            if actual:
                fragmentos.append(actual)
            actual = actual[-solape:] + "\n\n" + parrafo if actual else parrafo

    if actual:
        fragmentos.append(actual)

    return fragmentos


def procesar_vault(ruta_vault: str) -> list[dict]:
    """Devuelve una lista de fragmentos listos para indexar:
    [{"id": ..., "texto": ..., "metadata": {...}}, ...]"""
    fragmentos_totales: list[dict] = []

    for fichero_md in Path(ruta_vault).rglob("*.md"):
        post = frontmatter.load(fichero_md)
        metadata_base = dict(post.metadata)
        metadata_base["fuente"] = str(fichero_md.relative_to(ruta_vault))

        for i, fragmento in enumerate(trocear_texto(post.content)):
            id_fragmento = hashlib.sha256(
                f"{fichero_md}-{i}".encode()
            ).hexdigest()[:16]
            fragmentos_totales.append({
                "id": id_fragmento,
                "texto": fragmento,
                "metadata": metadata_base,
            })

    return fragmentos_totales


def main():
    parser = argparse.ArgumentParser(description="Ingesta del vault de Obsidian al RAG")
    parser.add_argument("--vault", required=True, help="Ruta al vault de Obsidian")
    parser.add_argument("--chroma-path", default="./chroma_data")
    args = parser.parse_args()

    fragmentos = procesar_vault(args.vault)
    print(f"Encontrados {len(fragmentos)} fragmentos en {args.vault}")

    store = RepositorioConocimientoChroma(ruta_datos=args.chroma_path)
    store.indexar_fragmentos(fragmentos)
    print("Ingesta completada.")


if __name__ == "__main__":
    main()
