#!/usr/bin/env python3
"""Deja la skill autocontenida y arma el .zip para subirla a la organización en Claude.

La skill lleva su propia copia de los íconos, del catálogo y de los scripts: en claude.ai el
entorno de ejecución solo sale por defecto a gestores de paquetes, así que no puede depender del
CDN para embeber. Los íconos van juntos en `iconos.json` y no uno por archivo, porque claude.ai
rechaza zips de más de 200 archivos. La fuente de verdad sigue siendo la raíz del repositorio
(`svg/`, que sirve el CDN, y `catalogo.json`); este script copia hacia la skill, nunca al revés.

Uso: empaquetar.py      # sincroniza skills/diagramas-oci/ y escribe dist/diagramas-oci.zip
"""
import json
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
    version = json.loads((RAIZ / "catalogo.json").read_text(encoding="utf-8"))["version"]
    iconos = {f.stem: f.read_text(encoding="utf-8") for f in sorted((RAIZ / "svg").glob("*.svg"))}
    (SKILL / "iconos.json").write_text(json.dumps(dict(version=version, iconos=iconos), ensure_ascii=False),
                                       encoding="utf-8")
    shutil.rmtree(SKILL / "svg", ignore_errors=True)  # formato anterior, un archivo por ícono


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
