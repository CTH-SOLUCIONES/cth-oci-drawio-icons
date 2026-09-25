#!/usr/bin/env python3
"""Deja en línea y canónicos los íconos OCI de un .drawio, para que el entregable no dependa de ninguna URL.

Cada ícono del catálogo lleva en su estilo `ociIcon=<slug>`. En cada celda con esa clave, este
script pone en `image=` el SVG canónico en línea, venga la imagen por URL o ya en línea. Si la
imagen ya venía en línea, como la escribe el agente para que se vea en el visor del MCP, una copia
mal transcrita queda corregida. Las celdas de diagramas anteriores a `ociIcon` se reconocen por la
URL del CDN.

El SVG sale de la carpeta `svg/` del repositorio o de `iconos.json` de la skill. Si el diagrama usa
íconos de otro toolkit, se descargan.

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

BASE = Path(__file__).resolve().parent.parent
SVG_LOCAL = BASE / "svg"  # el repositorio: un archivo por ícono
# La skill los lleva todos en un solo archivo, porque claude.ai rechaza zips de más de 200 archivos.
PAQUETE = BASE / "iconos.json"
URL_ICONO = re.compile(r"https://cdn\.jsdelivr\.net/gh/CTH-SOLUCIONES/cth-oci-drawio-icons@([^/]+)/svg/([a-z0-9-]+)\.svg")
_local: tuple[str, dict[str, bytes]] | None = None


def _toolkit(version: str) -> str:
    return version.rsplit(".", 1)[0]  # v24.2.2 → v24.2: las revisiones de este repo no cambian el dibujo


def _iconos_locales() -> tuple[str, dict[str, bytes]]:
    global _local
    if _local is None:
        if PAQUETE.exists():
            p = json.loads(PAQUETE.read_text(encoding="utf-8"))
            _local = (p["version"], {s: v.encode("utf-8") for s, v in p["iconos"].items()})
        else:
            version = json.loads((BASE / "catalogo.json").read_text(encoding="utf-8"))["version"]
            _local = (version, {f.stem: f.read_bytes() for f in SVG_LOCAL.glob("*.svg")})
    return _local


def _svg(slug: str, url: str | None) -> bytes | None:
    version, iconos = _iconos_locales()
    m = URL_ICONO.fullmatch(url or "")
    if m is None or _toolkit(m.group(1)) == _toolkit(version):
        return iconos.get(slug)
    with urllib.request.urlopen(url, timeout=30) as r:  # íconos de otro toolkit
        return r.read()


def _estilo(estilo: str, cuenta: dict) -> str:
    clave = re.search(r"(?:^|;)ociIcon=([a-z0-9-]+)", estilo)
    img = re.search(r"(?:^|;)image=([^;]*)", estilo)
    url = img.group(1) if img and img.group(1).startswith("https://") else None
    if clave is not None:
        slug = clave.group(1)
    else:
        m = URL_ICONO.fullmatch(url or "")
        if m is None:
            return estilo
        slug = m.group(2)
    svg = _svg(slug, url)
    if svg is None:
        cuenta["faltan"].append(slug)
        return estilo
    cuenta["total"] += 1
    # draw.io usa `data:<tipo>,<base64>` sin `;base64`: el `;` separa claves de estilo.
    nuevo = "data:image/svg+xml," + base64.b64encode(svg).decode()
    if img is None:
        return estilo.rstrip(";") + ";image=" + nuevo
    return estilo[:img.start(1)] + nuevo + estilo[img.end(1):]


def _inflar(contenido: str) -> str:
    return urllib.parse.unquote(zlib.decompress(base64.b64decode(contenido), -15).decode())


def embeber(texto: str) -> tuple[str, dict]:
    """Devuelve el archivo con los íconos en línea y la cuenta. Los diagramas comprimidos se
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
