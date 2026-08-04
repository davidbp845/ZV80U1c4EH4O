"""Comprueba que la ingesta del vault de Obsidian al RAG (Chroma) fue
bien: lanza una consulta contra el store ya indexado y muestra los
fragmentos que devuelve. No reindexa nada, solo lee lo que ya haya en
--chroma-path (ver adapters/out/obsidian_ingest.py para la ingesta).

Uso:
    python scripts/verificar_ingesta.py "¿cuáles son los precios?"
    python scripts/verificar_ingesta.py "horario" --top-k 5 --chroma-path ./chroma_data
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters.out.vector_store import RepositorioConocimientoChroma


def main():
    parser = argparse.ArgumentParser(description="Verifica el contenido indexado en el RAG")
    parser.add_argument("consulta", help="Pregunta a buscar en el vector store")
    parser.add_argument("--chroma-path", default="./chroma_data")
    parser.add_argument("--top-k", type=int, default=3)
    args = parser.parse_args()

    store = RepositorioConocimientoChroma(ruta_datos=args.chroma_path)
    fragmentos = store.buscar(args.consulta, top_k=args.top_k)

    if not fragmentos:
        print("Sin resultados: o el store está vacío, o la ingesta no llegó a indexar nada.")
        return

    for i, fragmento in enumerate(fragmentos, 1):
        print(f"--- Fragmento {i} ---")
        print(fragmento)
        print()


if __name__ == "__main__":
    main()
