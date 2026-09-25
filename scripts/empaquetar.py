#!/usr/bin/env python3
"""Deja la skill autocontenida y arma el .zip para subirla a la organización en Claude.

La skill lleva su propia copia del catálogo, que trae cada ícono como stencil en línea, y de los
scripts: en claude.ai el entorno de ejecución solo sale por defecto a gestores de paquetes, así que
no puede depender del CDN para embeber. Todo cabe en cuatro archivos; claude.ai rechaza zips de más
de 200. La fuente de verdad sigue siendo la raíz del repositorio; este script copia hacia la skill,
nunca al revés.

Uso: empaquetar.py      # sincroniza skills/diagramas-oci/ y escribe dist/diagramas-oci.zip
"""
import shutil
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "diagramas-oci"
COPIAS = {"catalogo.json": "catalogo.json",
          "scripts/embeber.py": "scripts/embeber.py", "scripts/buscar.py": "scripts/buscar.py"}
IGNORAR = {".DS_Store", "__pycache__"}
MAX_ARCHIVOS = 200  # lo que acepta la subida de skills en claude.ai


def sincronizar() -> None:
    for origen, destino in COPIAS.items():
        (SKILL / destino).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(RAIZ / origen, SKILL / destino)
    # formatos anteriores: un SVG por archivo, y después todos los SVG en iconos.json
    shutil.rmtree(SKILL / "svg", ignore_errors=True)
    (SKILL / "iconos.json").unlink(missing_ok=True)


def empaquetar() -> Path:
    # claude.ai exige la carpeta de la skill como raíz del zip, con el mismo nombre de la skill.
    archivos = [f for f in sorted(SKILL.rglob("*")) if f.is_file() and not IGNORAR.intersection(f.parts)]
    if len(archivos) > MAX_ARCHIVOS:
        raise SystemExit(f"la skill tiene {len(archivos)} archivos; claude.ai acepta hasta {MAX_ARCHIVOS}")
    salida = RAIZ / "dist" / f"{SKILL.name}.zip"
    salida.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        for f in archivos:
            z.write(f, Path(SKILL.name) / f.relative_to(SKILL))
    return salida


if __name__ == "__main__":
    sincronizar()
    zip_ = empaquetar()
    with zipfile.ZipFile(zip_) as z:
        n = len(z.namelist())
    print(f"skill sincronizada; {zip_.relative_to(RAIZ)}: {n} archivos, {zip_.stat().st_size / 1e6:.1f} MB")
