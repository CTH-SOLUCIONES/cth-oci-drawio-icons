#!/usr/bin/env python3
"""Busca íconos OCI en el catálogo sin cargarlo entero en el contexto del agente.

Uso:
  buscar.py <texto> [<texto>…]   # coincide con slug, etiqueta o categoría, sin tildes ni mayúsculas
  buscar.py --contenedores       # los 10 contenedores de la vista física, con su estilo
  buscar.py --estilo <slug>      # el estilo completo de un ícono, listo para pegar
"""
import json
import sys
import unicodedata
from pathlib import Path

CATALOGO = Path(__file__).resolve().parent.parent / "catalogo.json"


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def main() -> None:
    args = sys.argv[1:]
    if not args:
        sys.exit(__doc__)
    cat = json.loads(CATALOGO.read_text(encoding="utf-8"))
    if args[0] == "--contenedores":
        for c in cat["contenedores"]:
            print(f"{c['tipo']} | {c['etiqueta']} | {c['ancho']}x{c['alto']} | {c['estilo']}")
        return
    if args[0] == "--estilo":
        por_slug = {i["slug"]: i for i in cat["iconos"]}
        for s in args[1:]:
            i = por_slug.get(s)
            print(f"{s} | {i['ancho']}x{i['alto']} | {i['estilo']}" if i else f"{s} | no está en el catálogo")
        return
    terminos = [_norm(a) for a in args]
    hallados = [i for i in cat["iconos"]
                if all(t in _norm(f"{i['slug']} {i['etiqueta']} {i['categoria']}") for t in terminos)]
    for i in hallados:
        print(f"{i['slug']} | {i['etiqueta']} | {i['categoria']} | {i['ancho']}x{i['alto']}")
    if not hallados:
        print("sin coincidencias: prueba con el nombre en inglés o con menos palabras")


if __name__ == "__main__":
    main()
