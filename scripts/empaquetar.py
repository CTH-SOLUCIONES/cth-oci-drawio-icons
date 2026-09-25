#!/usr/bin/env python3
"""Deja la skill autocontenida y arma el .zip para subirla a la organización en Claude.

La skill lleva su propia copia de los íconos, del catálogo y de los scripts: en claude.ai el
entorno de ejecución solo sale por defecto a gestores de paquetes, así que no puede depender del
CDN para embeber. La fuente de verdad sigue siendo la raíz del repositorio (`svg/`, que sirve el
CDN, y `catalogo.json`); este script copia hacia la skill, nunca al revés.

Uso: empaquetar.py      # sincroniza skills/diagramas-oci/ y escribe dist/diagramas-oci.zip
"""
import shutil
import zipfile
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
SKILL = RAIZ / "skills" / "diagramas-oci"
COPIAS = {"svg": "svg", "catalogo.json": "catalogo.json",
          "scripts/embeber.py": "scripts/embeber.py", "scripts/buscar.py": "scripts/buscar.py"}
IGNORAR = {".DS_Store", "__pycache__"}


def sincronizar() -> None:
    for origen, destino in COPIAS.items():
        o, d = RAIZ / origen, SKILL / destino
        if o.is_dir():
            shutil.rmtree(d, ignore_errors=True)
            shutil.copytree(o, d, ignore=shutil.ignore_patterns(*IGNORAR))
        else:
            d.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(o, d)


def empaquetar() -> Path:
    # claude.ai exige la carpeta de la skill como raíz del zip, con el mismo nombre de la skill.
    salida = RAIZ / "dist" / f"{SKILL.name}.zip"
    salida.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(salida, "w", zipfile.ZIP_DEFLATED) as z:
        for f in sorted(SKILL.rglob("*")):
            if f.is_file() and not IGNORAR.intersection(f.parts):
                z.write(f, Path(SKILL.name) / f.relative_to(SKILL))
    return salida


if __name__ == "__main__":
    sincronizar()
    zip_ = empaquetar()
    print(f"skill sincronizada; {zip_.relative_to(RAIZ)} ({zip_.stat().st_size / 1e6:.1f} MB)")
