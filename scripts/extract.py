#!/usr/bin/env python3
"""Extract the icons of Oracle's OCI Architecture Diagram Toolkit into one SVG per icon and build the catalog.

It segments the "Icons" page by position (shapes that touch each other = one pictogram; the text
right below it = its label; the closest heading above it = its category), exports each pictogram
with the draw.io CLI, slims it down with `optimize.py`, converts it to a stencil with `stencil.py`
and takes the containers from the legend of the "Physical" page. It writes `svg/`, `catalog.json`
and `catalog.md`.

Usage:
  OCI_TOOLKIT=<toolkit.drawio> extract.py
  extract.py <toolkit.drawio>

The toolkit is Oracle's "OCI Architecture Diagram Toolkit v24.2.drawio"; it is not in this
repository. The draw.io desktop binary comes from DRAWIO_BIN (default
/Applications/draw.io.app/Contents/MacOS/draw.io); `npx` (Node) is also required.
"""
import base64
import collections
import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import urllib.parse
import xml.etree.ElementTree as ET
import xml.sax.saxutils as saxutils
import zlib
from pathlib import Path

import stencil

# ----------------------------------------------------------------------------- catalog constants
REPO = "CTH-SOLUCIONES/cth-oci-drawio-icons"
VERSION = "v24.2.4"  # release of this repo; the source of the catalog files. The other places that carry it are listed in CONTRIBUTING.md and checked by tests/test_version.py
TOOLKIT_VERSION = VERSION.rsplit(".", 1)[0]  # v24.2: Oracle's toolkit; the last digit is this repo's revision
SOURCE = f"OCI Architecture Diagram Toolkit {TOOLKIT_VERSION} (Oracle): Icons page, and the legend of the Physical page"
BASE_URL = f"https://cdn.jsdelivr.net/gh/{REPO}@{VERSION}/svg"
DEFAULT_DRAWIO_BIN = "/Applications/draw.io.app/Contents/MacOS/draw.io"
# `ociIcon` is not a draw.io key, which keeps the keys it does not know: it identifies the icon in
# any form, so that `embed.py` can leave it canonical.
BASE_STYLE = ("html=1;verticalLabelPosition=bottom;verticalAlign=top;labelBackgroundColor=none;aspect=fixed;"
              "fontFamily=Oracle Sans;fontSize=11;fontColor=#312D2A;ociIcon={slug};")
# Inline: the MCP viewer draws it without loading anything. By URL: lightweight, but the viewer does not load it.
STENCIL_STYLE = "shape=stencil({stencil});" + BASE_STYLE
URL_STYLE = "shape=image;imageAspect=0;" + BASE_STYLE + "image={url}"
CONTAINERS = {  # type -> label that identifies it in the legend of the Physical page
    "region": "OCI Region", "availability-domain": "Availability Domain", "fault-domain": "Fault Domain",
    "tenancy": "Tenancy", "compartment": "Compartment A", "vcn": "VCN", "subnet": "Subnet 0.0.0.0/00",
    "oke-cluster": "Container Engine for Kubernetes Cluster", "on-premises": "On-Premises", "internet": "Internet",
}
# Geometry of the segmentation, in draw.io units (px).
TOUCH_TOLERANCE = 2        # shapes closer than this are one pictogram
MAX_SHAPE_SIZE = 150       # larger shapes are frames or backgrounds, not pictogram parts
LABEL_MAX_GAP = 40         # a label's top edge falls at most this far below the pictogram
LABEL_CENTER_SLACK = 5     # tolerance on top of half the widest of pictogram and label


# ----------------------------------------------------------------------------- reading the toolkit
def toolkit_path(args: list[str]) -> Path:
    """The toolkit file, from the first argument or from OCI_TOOLKIT; fails with a clear message if missing."""
    given = args[0] if args else os.environ.get("OCI_TOOLKIT")
    if not given:
        sys.exit("toolkit not given: set OCI_TOOLKIT or pass the path of "
                 "'OCI Architecture Diagram Toolkit v24.2.drawio' as the first argument")
    path = Path(given).expanduser()
    if not path.is_file():
        sys.exit(f"toolkit file not found: {path}")
    return path


def drawio_binary() -> str:
    """The draw.io desktop binary, from DRAWIO_BIN or the default macOS location; fails if missing."""
    binary = os.environ.get("DRAWIO_BIN", DEFAULT_DRAWIO_BIN)
    if not Path(binary).is_file():
        sys.exit(f"draw.io binary not found: {binary} (set DRAWIO_BIN)")
    return binary


def inflate(content: str) -> str:
    """Decode a compressed diagram body (base64, raw deflate, URL-encoded); anything else comes back unchanged."""
    try:
        return urllib.parse.unquote(zlib.decompress(base64.b64decode(content), -15).decode())
    except Exception:
        return content


def read_page(toolkit: Path, name: str) -> ET.Element:
    """The XML root of the page called `name` in the toolkit."""
    text = toolkit.read_text(encoding="utf-8")
    pages = [body for attrs, body in re.findall(r"<diagram([^>]*)>(.*?)</diagram>", text, re.S)
             if f'name="{name}"' in attrs]
    if not pages:
        sys.exit(f"page {name!r} not found in {toolkit}")
    body = pages[0]
    return ET.fromstring(body if body.strip().startswith("<") else inflate(body.strip()))


def plain_text(value: str | None) -> str:
    """The visible text of a cell value: markup removed, entities decoded, whitespace collapsed."""
    without_tags = re.sub(r"<[^>]+>", " ", html.unescape(value or ""))
    return re.sub(r"\s+", " ", html.unescape(without_tags)).strip()


class Cell:
    """An mxCell with its attributes and XML element; `<object>`/`<UserObject>` wrappers are already resolved."""

    def __init__(self, attrs: dict, element: ET.Element):
        self.attrs = attrs
        self.element = element

    def get(self, key: str, default=None):
        return self.attrs.get(key, default)

    def find(self, tag: str):
        return self.element.find(tag)


def read_cells(root: ET.Element) -> list[Cell]:
    """Every cell with id, parent, style, value and geometry, resolving the `<object>`/`<UserObject>`
    wrappers, which carry the id and the label outside the mxCell."""
    cells = []
    for el in root.iter():
        if el.tag in ("object", "UserObject"):
            inner = el.find("mxCell")
            if inner is None:
                continue
            attrs = dict(inner.attrib)
            attrs["id"] = el.get("id")
            attrs["value"] = el.get("label", el.get("value", ""))
            cells.append(Cell(attrs, inner))
        elif el.tag == "mxCell" and el.get("id") is not None:
            cells.append(Cell(dict(el.attrib), el))
    return cells


def _geometry(cell: Cell) -> list[float] | None:
    """[x, y, width, height] of a cell, or None if it has no geometry."""
    geometry = cell.find("mxGeometry")
    if geometry is None:
        return None
    return [float(geometry.get(k, 0)) for k in ("x", "y", "width", "height")]


def _parent_offset(cell: Cell, by_id: dict[str, Cell]) -> tuple[float, float]:
    """Sum of the positions of the cell's ancestors (the top-level layers, ids 0 and 1, do not count)."""
    x = y = 0.0
    current = cell
    while current is not None and current.get("parent") not in (None, "0", "1"):
        parent = by_id.get(current.get("parent"))
        if parent is None:
            break
        geometry = _geometry(parent)
        if geometry:
            x += geometry[0]
            y += geometry[1]
        current = parent
    return x, y


def shapes_of(root: ET.Element) -> list[dict]:
    """The vertices of a page with absolute position, size, style and visible text."""
    cells = read_cells(root)
    by_id = {c.get("id"): c for c in cells}
    shapes = []
    for cell in cells:
        if cell.get("vertex") != "1":
            continue
        style = cell.get("style") or ""
        if style.startswith("group"):
            continue
        geometry = _geometry(cell)
        if not geometry:
            continue
        offset_x, offset_y = _parent_offset(cell, by_id)
        shapes.append(dict(id=cell.get("id"), x=geometry[0] + offset_x, y=geometry[1] + offset_y,
                           w=geometry[2], h=geometry[3], style=style, text=plain_text(cell.get("value")),
                           cell=cell))
    return shapes


# ----------------------------------------------------------------------------- segmentation
def _is_invisible(shape: dict) -> bool:
    style = shape["style"]
    return ("fillColor=none" in style or "fillColor" not in style) and "strokeColor=none" in style


def label_candidates(icon: dict, texts: list[dict]) -> list[dict]:
    """The texts that sit right below the pictogram, centered on it: the pieces of its label."""
    center = icon["x"] + icon["w"] / 2
    return [t for t in texts
            if 0 <= t["y"] - (icon["y"] + icon["h"]) <= LABEL_MAX_GAP
            and abs((t["x"] + t["w"] / 2) - center) <= max(icon["w"], t["w"]) / 2 + LABEL_CENTER_SLACK]


def _group_touching(shapes: list[dict]) -> list[list[dict]]:
    """Union-find over the shapes that touch (within TOUCH_TOLERANCE px); one group per pictogram."""
    parent = list(range(len(shapes)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    by_x = sorted(range(len(shapes)), key=lambda i: shapes[i]["x"])
    for a in range(len(by_x)):
        i = by_x[a]
        first = shapes[i]
        for b in range(a + 1, len(by_x)):
            j = by_x[b]
            second = shapes[j]
            if second["x"] > first["x"] + first["w"] + TOUCH_TOLERANCE:
                break
            apart_vertically = (second["y"] > first["y"] + first["h"] + TOUCH_TOLERANCE
                                or first["y"] > second["y"] + second["h"] + TOUCH_TOLERANCE)
            if not apart_vertically:
                parent[find(i)] = find(j)
    groups = collections.defaultdict(list)
    for i, shape in enumerate(shapes):
        groups[find(i)].append(shape)
    return list(groups.values())


def segment(root: ET.Element) -> tuple[list[dict], list[dict]]:
    """Split the Icons page into pictograms (with their label) and return them with all the texts."""
    shapes = shapes_of(root)
    texts = [s for s in shapes if s["text"]]
    parts = [s for s in shapes
             if not s["text"] and not _is_invisible(s) and s["w"] <= MAX_SHAPE_SIZE and s["h"] <= MAX_SHAPE_SIZE]
    icons = []
    for group in _group_touching(parts):
        x0 = min(s["x"] for s in group)
        y0 = min(s["y"] for s in group)
        x1 = max(s["x"] + s["w"] for s in group)
        y1 = max(s["y"] + s["h"] for s in group)
        icons.append(dict(parts=group, x=x0, y=y0, w=x1 - x0, h=y1 - y0))
    for icon in icons:
        candidates = sorted(label_candidates(icon, texts), key=lambda t: (t["y"], t["x"]))
        icon["label"] = " ".join(t["text"] for t in candidates).strip()
    return icons, texts


def assign_categories(icons: list[dict], texts: list[dict]) -> None:
    """Each pictogram's category is the closest text above it that is not anybody's label."""
    used = {t["id"] for icon in icons for t in label_candidates(icon, texts)}
    headings = sorted([t for t in texts if t["id"] not in used], key=lambda t: t["y"])
    for icon in icons:
        above = [h for h in headings if h["y"] <= icon["y"]]
        icon["category"] = above[-1]["text"] if above else "Other"


# ----------------------------------------------------------------------------- export
def make_slug(label: str) -> str:
    """`OCI Compute` -> `compute`: ASCII, lowercase, hyphen-separated, without the leading `OCI`."""
    text = unicodedata.normalize("NFKD", label).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"^oci\s+", "", text)
    return re.sub(r"[^a-z0-9]+", "-", text).strip("-")


def drawio_of(icon: dict) -> str:
    """A one-page .drawio file with the parts of the pictogram placed at the origin."""
    x0, y0 = icon["x"], icon["y"]
    cells = []
    for k, part in enumerate(icon["parts"]):
        style = saxutils.escape(part["style"], {'"': "&quot;"})
        cells.append(f'<mxCell id="c{k}" value="" style="{style}" vertex="1" parent="1">'
                     f'<mxGeometry x="{part["x"] - x0:.3f}" y="{part["y"] - y0:.3f}" '
                     f'width="{part["w"]:.3f}" height="{part["h"]:.3f}" as="geometry"/></mxCell>')
    return ('<mxfile><diagram name="icon" id="i"><mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>'
            + "".join(cells) + "</root></mxGraphModel></diagram></mxfile>")


def read_containers(toolkit: Path) -> list[dict]:
    """The container samples of the legend of the Physical page, one per type in CONTAINERS."""
    shapes = shapes_of(read_page(toolkit, "Physical"))
    found = []
    for kind, label in CONTAINERS.items():
        candidates = [s for s in shapes if s["text"].startswith(label) and s["w"] > 80 and s["h"] > 40]
        candidates.sort(key=lambda s: s["w"] * s["h"])  # the legend sample is the smallest
        if candidates:
            best = candidates[0]
            found.append(dict(type=kind, label=label, style=best["style"],
                              width=round(best["w"]), height=round(best["h"])))
    return found


def write_markdown(icons: list[dict], containers: list[dict], path: Path) -> None:
    """The human-readable catalog: icons by category, then the containers."""
    lines = ["# OCI icon catalog for draw.io", "",
             f"Toolkit {TOOLKIT_VERSION} (release {VERSION}). Base style of each icon in `catalog.json`; "
             f"URL: `{BASE_URL}/<slug>.svg`.", ""]
    for category in sorted({i["category"] for i in icons}):
        lines += [f"## {category}", "", "| slug | Official label | Size |", "|---|---|---|"]
        lines += [f"| `{i['slug']}` | {i['label']} | {i['width']}×{i['height']} |"
                  for i in icons if i["category"] == category]
        lines.append("")
    lines += ["## Containers (physical view)", "", "| type | Label in the toolkit | Reference size |", "|---|---|---|"]
    lines += [f"| `{c['type']}` | {c['label']} | {c['width']}×{c['height']} |" for c in containers]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(args: list[str]) -> None:
    toolkit = toolkit_path(args)
    drawio = drawio_binary()
    root = Path(__file__).resolve().parent.parent
    icons, texts = segment(read_page(toolkit, "Icons"))
    assign_categories(icons, texts)
    icons.sort(key=lambda i: (i["y"], i["x"]))

    seen = collections.Counter()
    catalog = []
    workdir = tempfile.mkdtemp()
    for icon in icons:
        base = make_slug(icon["label"]) or "icon"
        seen[base] += 1
        slug = base if seen[base] == 1 else f"{base}-{seen[base]}"
        (Path(workdir) / f"{slug}.drawio").write_text(drawio_of(icon), encoding="utf-8")
        catalog.append(dict(slug=slug, label=icon["label"], category=icon["category"],
                            width=round(icon["w"]), height=round(icon["h"]), file=f"svg/{slug}.svg",
                            style=None,  # filled in below, once the SVG exists
                            url_style=URL_STYLE.format(slug=slug, url=f"{BASE_URL}/{slug}.svg")))
    svg_dir = root / "svg"
    svg_dir.mkdir(exist_ok=True)
    # `--theme light`: without it, draw.io exports adaptive colors (light-dark) and in a dark viewer
    # the white interior of the icons comes out black.
    subprocess.run([drawio, "-x", "-f", "svg", "-b", "0", "--theme", "light", "-o", str(svg_dir), workdir],
                   check=True, capture_output=True)
    shutil.rmtree(workdir)
    subprocess.run([sys.executable, str(root / "scripts" / "optimize.py"), str(svg_dir)], check=True)
    for entry in catalog:
        svg = (root / entry["file"]).read_text(encoding="utf-8")
        entry["style"] = STENCIL_STYLE.format(stencil=stencil.stencil(svg), slug=entry["slug"])

    containers = read_containers(toolkit)
    with open(root / "catalog.json", "w", encoding="utf-8") as out:
        json.dump(dict(source=SOURCE, version=VERSION, base_url=BASE_URL, icons=catalog, containers=containers),
                  out, ensure_ascii=False, indent=1)
    write_markdown(catalog, containers, root / "catalog.md")
    print(f"{len(catalog)} icons exported to svg/ and catalog written")


if __name__ == "__main__":
    main(sys.argv[1:])
