#!/usr/bin/env python3
"""Busca íconos OCI en el catálogo y da su estilo, sin cargar el catálogo entero en el contexto del agente.

Uso:
  buscar.py <texto> [<texto>…]   # coincide con slug, etiqueta o categoría, sin tildes ni mayúsculas
  buscar.py --estilo <slug>…     # estilo con el SVG en línea: se ve en el visor del MCP de draw.io
  buscar.py --url <slug>…        # estilo con el ícono por URL: liviano, pero el visor no lo muestra
  buscar.py --contenedores       # los 10 contenedores de la vista física, con su estilo
"""
import base64
import json
import re
import sys
import unicodedata
from pathlib import Path

BASE = Path(__file__).resolve().parent.parent
CATALOGO = BASE / "catalogo.json"
PAQUETE = BASE / "iconos.json"  # en la skill; en el repositorio los SVG están en svg/


def _norm(s: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


def _svg(slug: str) -> bytes:
    if PAQUETE.exists():
        return json.loads(PAQUETE.read_text(encoding="utf-8"))["iconos"][slug].encode("utf-8")
    return (BASE / "svg" / f"{slug}.svg").read_bytes()


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
        for s in args[1:]:
            i = por_slug.get(s)
            if i is None:
                print(f"{s} | no está en el catálogo")
                continue
            estilo = i["estilo"]
            if args[0] == "--estilo":
                # draw.io usa `data:<tipo>,<base64>` sin `;base64`: el `;` separa claves de estilo.
                estilo = re.sub(r"image=[^;]*$", "image=data:image/svg+xml," + base64.b64encode(_svg(s)).decode(), estilo)
            print(f"{s} | {i['ancho']}x{i['alto']} | {estilo}")
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
