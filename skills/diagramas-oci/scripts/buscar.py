#!/usr/bin/env python3
"""Busca íconos OCI en el catálogo y da su estilo, sin cargar el catálogo entero en el contexto del agente.

Uso:
  buscar.py <texto> [<texto>…]   # coincide con slug, etiqueta o categoría, sin tildes ni mayúsculas
  buscar.py --estilo <slug>…     # estilo en línea (stencil): se ve en el visor del MCP de draw.io
  buscar.py --url <slug>…        # estilo por URL: liviano, pero el visor del MCP no lo muestra
  buscar.py --contenedores       # los 10 contenedores de la vista física, con su estilo

Con --estilo, al final suma lo que pesan los estilos pedidos contra el presupuesto del XML.
"""
import json
import sys
import unicodedata
from pathlib import Path

CATALOGO = Path(__file__).resolve().parent.parent / "catalogo.json"
# `create_diagram` devuelve el XML entero, y el cliente corta los resultados de más de 25.000 tokens:
# un XML de unos 50 KB ya no llegó al visor. 30.000 caracteres deja margen para contenedores y flechas.
PRESUPUESTO = 30_000


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
    if args[0] in ("--estilo", "--url"):
        por_slug = {i["slug"]: i for i in cat["iconos"]}
        clave = "estilo" if args[0] == "--estilo" else "estilo_url"
        total = 0
        for s in args[1:]:
            i = por_slug.get(s)
            if i is None:
                print(f"{s} | no está en el catálogo")
                continue
            total += len(i[clave])
            print(f"{s} | {i['ancho']}x{i['alto']} | {i[clave]}")
        if clave == "estilo":
            print(f"# {total} caracteres en estilos (cada celda que repita un ícono suma el suyo otra vez); "
                  f"el XML completo debe quedar bajo {PRESUPUESTO}"
                  + ("" if total < PRESUPUESTO * 0.8 else ": no cabe, usa --url y avisa que el visor no mostrará los íconos"))
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
