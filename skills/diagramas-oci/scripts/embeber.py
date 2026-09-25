#!/usr/bin/env python3
"""Embebe los íconos OCI de un .drawio para que el entregable no dependa de ninguna URL.

Un diagrama se diseña con el MCP de draw.io referenciando los íconos por URL (estilos cortos,
el XML cabe en una llamada). Antes de entregarlo, este script reemplaza cada
`image=https://cdn.jsdelivr.net/gh/CTH-SOLUCIONES/cth-oci-drawio-icons@<versión>/svg/<slug>.svg`
por el SVG en línea, tomado de la carpeta `svg/` de este repositorio (o descargado si no está).

Uso:
  embeber.py diagrama.drawio              # escribe diagrama.drawio embebido (guarda .bak)
  embeber.py diagrama.drawio salida.drawio
"""
import base64
import re
import sys
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

SVG_LOCAL = Path(__file__).resolve().parent.parent / "svg"
URL_ICONO = re.compile(r"image=(https://cdn\.jsdelivr\.net/gh/CTH-SOLUCIONES/cth-oci-drawio-icons@[^/]+/svg/([a-z0-9-]+)\.svg)")


def _svg(url: str, slug: str) -> bytes:
    local = SVG_LOCAL / f"{slug}.svg"
    if local.exists():
        return local.read_bytes()
    with urllib.request.urlopen(url, timeout=30) as r:  # ícono de una versión que no está en disco
        return r.read()


def _inflar(contenido: str) -> str:
    return urllib.parse.unquote(zlib.decompress(base64.b64decode(contenido), -15).decode())


def embeber(texto: str) -> tuple[str, int]:
    """Devuelve el archivo con los íconos en línea y cuántos reemplazó. Los diagramas
    comprimidos se descomprimen: draw.io abre igual el XML plano."""
    total = 0

    def reemplazar(xml: str) -> str:
        nonlocal total
        def uno(m):
            nonlocal total
            total += 1
            # draw.io usa `data:<tipo>,<base64>` sin `;base64`: el `;` separa claves de estilo.
            return "image=data:image/svg+xml," + base64.b64encode(_svg(m.group(1), m.group(2))).decode()
        return URL_ICONO.sub(uno, xml)

    def diagrama(m):
        abre, cuerpo, cierra = m.group(1), m.group(2), m.group(3)
        if cuerpo.strip() and not cuerpo.strip().startswith("<"):
            cuerpo = _inflar(cuerpo.strip())
        return abre + reemplazar(cuerpo) + cierra

    if "<diagram" in texto:
        texto = re.sub(r"(<diagram[^>]*>)(.*?)(</diagram>)", diagrama, texto, flags=re.S)
    else:  # XML suelto, como el que devuelve el MCP
        texto = reemplazar(texto)
    return texto, total


def main() -> None:
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    entrada = Path(sys.argv[1])
    salida = Path(sys.argv[2]) if len(sys.argv) == 3 else entrada
    texto, n = embeber(entrada.read_text(encoding="utf-8"))
    if salida == entrada:
        entrada.with_suffix(entrada.suffix + ".bak").write_text(entrada.read_text(encoding="utf-8"), encoding="utf-8")
    salida.write_text(texto, encoding="utf-8")
    quedan = len(re.findall(r"image=https?://", texto))
    print(f"{n} íconos embebidos en {salida}" + (f"; quedan {quedan} imágenes por URL que no son de este repositorio" if quedan else ""))


if __name__ == "__main__":
    main()
