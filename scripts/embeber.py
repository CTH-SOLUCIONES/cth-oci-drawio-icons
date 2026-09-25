#!/usr/bin/env python3
"""Deja canónicos y en línea los íconos OCI de un .drawio, para que el entregable no dependa de ninguna URL.

Cada ícono del catálogo lleva en su estilo `ociIcon=<slug>`. En cada celda con esa clave, este
script pone la forma canónica del catálogo: el stencil en línea (`shape=stencil(…)`). Da igual si el
ícono venía por URL, como stencil o como imagen en línea de una versión anterior. Si el agente
transcribió mal un stencil, queda corregido. Las demás claves de estilo de la celda se conservan.
Las celdas de diagramas anteriores a `ociIcon` se reconocen por la URL del CDN.

Todo sale de `catalogo.json`, sin red. Si el diagrama usa íconos de otro toolkit, se descargan y
quedan como imagen en línea.

Uso:
  embeber.py diagrama.drawio              # escribe diagrama.drawio embebido (guarda .bak)
  embeber.py diagrama.drawio salida.drawio
"""
import base64
import json
import re
import sys
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

CATALOGO = Path(__file__).resolve().parent.parent / "catalogo.json"
URL_ICONO = re.compile(r"https://cdn\.jsdelivr\.net/gh/CTH-SOLUCIONES/cth-oci-drawio-icons@([^/]+)/svg/([a-z0-9-]+)\.svg")
QUITAR = {"shape", "image", "imageAspect"}  # las pone la forma canónica, o dejan de aplicar
_cat: tuple[str, dict[str, str]] | None = None


def _toolkit(version: str) -> str:
    return version.rsplit(".", 1)[0]  # v24.2.3 → v24.2: las revisiones de este repo no cambian el dibujo


def _catalogo() -> tuple[str, dict[str, str]]:
    global _cat
    if _cat is None:
        c = json.loads(CATALOGO.read_text(encoding="utf-8"))
        _cat = (c["version"], {i["slug"]: i["estilo"] for i in c["iconos"]})
    return _cat


def _claves(estilo: str) -> list[tuple[str, str | None]]:
    """El estilo como lista ordenada de (clave, valor); `None` para entradas sin `=`, como `ellipse`."""
    out = []
    for parte in estilo.split(";"):
        if parte:
            k, _, v = parte.partition("=")
            out.append((k, v if _ else None))
    return out


def _estilo(estilo: str, cuenta: dict) -> str:
    claves = _claves(estilo)
    d = dict(claves)
    url = d.get("image") if (d.get("image") or "").startswith("https://") else None
    m = URL_ICONO.fullmatch(url or "")
    slug = d.get("ociIcon") or (m.group(2) if m else None)
    if slug is None:
        return estilo
    version, iconos = _catalogo()
    if m is not None and _toolkit(m.group(1)) != _toolkit(version):  # íconos de otro toolkit
        with urllib.request.urlopen(url, timeout=30) as r:
            cuenta["total"] += 1
            # draw.io usa `data:<tipo>,<base64>` sin `;base64`: el `;` separa claves de estilo.
            d["image"] = "data:image/svg+xml," + base64.b64encode(r.read()).decode()
            return ";".join(k if v is None else f"{k}={d[k]}" for k, v in claves) + ";"
    canon = iconos.get(slug)
    if canon is None:
        cuenta["faltan"].append(slug)
        return estilo
    cuenta["total"] += 1
    canon_claves = _claves(canon)
    propias = {k for k, _ in canon_claves}
    # La forma canónica primero; después, lo que la celda agregó o cambió (tamaño de letra, posición…).
    resto = [(k, v) for k, v in claves if k not in QUITAR and k not in propias]
    cambios = {k: v for k, v in claves if k in propias and k not in QUITAR}
    return ";".join(k if v is None else f"{k}={cambios.get(k, v)}" for k, v in canon_claves + resto) + ";"


def _inflar(contenido: str) -> str:
    return urllib.parse.unquote(zlib.decompress(base64.b64decode(contenido), -15).decode())


def embeber(texto: str) -> tuple[str, dict]:
    """Devuelve el archivo con los íconos canónicos y la cuenta. Los diagramas comprimidos se
    descomprimen: draw.io abre igual el XML plano."""
    cuenta = {"total": 0, "faltan": []}

    def reemplazar(xml: str) -> str:
        return re.sub(r'style="([^"]*)"', lambda m: 'style="' + _estilo(m.group(1), cuenta) + '"', xml)

    def diagrama(m):
        abre, cuerpo, cierra = m.group(1), m.group(2), m.group(3)
        if cuerpo.strip() and not cuerpo.strip().startswith("<"):
            cuerpo = _inflar(cuerpo.strip())
        return abre + reemplazar(cuerpo) + cierra

    if "<diagram" in texto:
        texto = re.sub(r"(<diagram[^>]*>)(.*?)(</diagram>)", diagrama, texto, flags=re.S)
    else:  # XML suelto, como el que recibe el MCP
        texto = reemplazar(texto)
    return texto, cuenta


def main() -> None:
    if len(sys.argv) not in (2, 3):
        sys.exit(__doc__)
    entrada = Path(sys.argv[1])
    salida = Path(sys.argv[2]) if len(sys.argv) == 3 else entrada
    texto, cuenta = embeber(entrada.read_text(encoding="utf-8"))
    if salida == entrada:
        entrada.with_suffix(entrada.suffix + ".bak").write_text(entrada.read_text(encoding="utf-8"), encoding="utf-8")
    salida.write_text(texto, encoding="utf-8")
    quedan = len(re.findall(r"image=https?://", texto))
    print(f"{cuenta['total']} íconos embebidos en {salida}"
          + (f"; sin ícono en el catálogo: {', '.join(sorted(set(cuenta['faltan'])))}" if cuenta["faltan"] else "")
          + (f"; quedan {quedan} imágenes por URL que no son de este repositorio" if quedan else ""))


if __name__ == "__main__":
    main()
