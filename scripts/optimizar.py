#!/usr/bin/env python3
"""Adelgaza los SVG que exporta draw.io para que quepan embebidos en el XML del MCP.

El visor del MCP de draw.io solo carga imágenes de diagrams.net o en línea (`data:`), así que para
que los íconos se vean en el chat van embebidos en la llamada, y cada byte se escribe. Este script
quita lo que draw.io agrega para su editor (ids de celda, pointer-events, estilos que repiten el
atributo, el fondo del lienzo) y pasa SVGO con precisión de 0,1 px, que en un ícono de 42 px no se ve.

Uso: optimizar.py [carpeta]   # por defecto svg/, en el lugar; exige npx (Node)
"""
import re
import subprocess
import sys
from pathlib import Path

SVGO = "svgo@4.1.0"  # fijada: otra versión puede producir otros bytes para los mismos íconos


def limpiar(svg: str) -> str:
    svg = re.sub(r"<\?xml[^>]*\?>|<!DOCTYPE[^>]*>", "", svg)
    svg = re.sub(r'\s(?:data-cell-id|pointer-events)="[^"]*"', "", svg)
    # draw.io repite fill y stroke en `style`; los atributos ya los traen. Sin los ids ni esto,
    # SVGO puede fundir los trazos del mismo color en uno solo.
    svg = re.sub(r'\sstyle="(?:fill|stroke): [^"]*"', "", svg)
    return re.sub(r'(<svg[^>]*?)\sstyle="[^"]*"', r"\1", svg, count=1)  # fondo y color-scheme del lienzo


def main() -> None:
    carpeta = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "svg"
    archivos = sorted(carpeta.glob("*.svg"))
    antes = sum(f.stat().st_size for f in archivos)
    for f in archivos:
        f.write_text(limpiar(f.read_text(encoding="utf-8")), encoding="utf-8")
    subprocess.run(["npx", "-y", SVGO, "--multipass", "-p", "2", "-q", "-f", str(carpeta), "-o", str(carpeta)],
                   check=True)
    despues = sum(f.stat().st_size for f in archivos)
    print(f"{len(archivos)} SVG optimizados: {antes / 1e3:.0f} KB → {despues / 1e3:.0f} KB")


if __name__ == "__main__":
    main()
