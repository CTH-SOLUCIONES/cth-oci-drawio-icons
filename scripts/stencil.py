#!/usr/bin/env python3
"""Convierte los SVG de los íconos en stencils de draw.io: vectoriales, comprimidos y sin imagen externa.

La respuesta de `create_diagram` repite el XML entero. Con los íconos como SVG en línea (base64),
una vista mediana superaba el tope de tokens que el cliente admite para el resultado de una
herramienta, y el visor recibía el aviso de error en vez del diagrama. Un stencil comprimido
(`shape=stencil(…)`) pesa un 37 % menos en los íconos más usados, lo dibuja el visor sin cargar nada
y es el mismo formato con que draw.io guarda las formas propias. Las coordenadas van absolutas y
redondeadas a 0,1 px: sin acumular error, como pasaba con las relativas de SVGO a esa precisión.

Solo cubre lo que traen estos SVG: `<path>` con `fill`, y un trazo con `stroke`, sin `transform`
ni `fill-rule`. Si un SVG trae otra cosa, falla en lugar de dibujar algo distinto.

Uso: stencil.py <archivo.svg>   # imprime el valor de `shape=stencil(…)`
"""
import base64
import re
import sys
import xml.etree.ElementTree as ET
import zlib

NS = "{http://www.w3.org/2000/svg}"
_NUM = re.compile(r"[-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?")


def _f(v: float) -> str:
    s = f"{v:.1f}".rstrip("0").rstrip(".")
    return "0" if s in ("", "-0") else s


def _tokens(d: str):
    """Comandos y números de un atributo `d`, respetando las banderas de arco compactadas por SVGO
    (`a2 2 0 012 2` son las banderas 0 y 1 seguidas de 2)."""
    i, n, cmd, idx = 0, len(d), None, 0
    while i < n:
        c = d[i]
        if c in " ,\t\n":
            i += 1
            continue
        if c.isalpha():
            cmd, idx = c, 0
            yield c
            i += 1
            continue
        if cmd in "Aa" and idx % 7 in (3, 4):
            yield c  # bandera de arco: un solo carácter
            i += 1
        else:
            m = _NUM.match(d, i)
            if not m:
                raise ValueError(f"no entiendo {d[i:i + 20]!r}")
            yield m.group()
            i = m.end()
        idx += 1


def _path(d: str) -> str:
    """Traduce un `d` de SVG a los elementos de path de un stencil, en coordenadas absolutas."""
    out, toks, x, y, sx, sy = [], list(_tokens(d)), 0.0, 0.0, 0.0, 0.0
    prev_c = prev_q = None  # último punto de control, para S y T
    i, cmd = 0, None
    while i < len(toks):
        if toks[i].isalpha():
            cmd = toks[i]
            i += 1
            if cmd in "Zz":
                out.append("<close/>")
                x, y, prev_c, prev_q = sx, sy, None, None
                continue
        rel = cmd.islower()
        C = cmd.upper()
        aridad = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}[C]
        a = [float(t) for t in toks[i:i + aridad]]
        i += aridad
        if C == "M":
            x, y = (x + a[0], y + a[1]) if rel else (a[0], a[1])
            sx, sy = x, y
            out.append(f'<move x="{_f(x)}" y="{_f(y)}"/>')
            cmd = "l" if rel else "L"  # pares siguientes a un M son líneas
            prev_c = prev_q = None
        elif C in "LHV":
            if C == "L":
                x, y = (x + a[0], y + a[1]) if rel else (a[0], a[1])
            elif C == "H":
                x = x + a[0] if rel else a[0]
            else:
                y = y + a[0] if rel else a[0]
            out.append(f'<line x="{_f(x)}" y="{_f(y)}"/>')
            prev_c = prev_q = None
        elif C in "CS":
            if C == "C":
                p = [(x + a[k], y + a[k + 1]) if rel else (a[k], a[k + 1]) for k in (0, 2, 4)]
            else:
                c1 = (2 * x - prev_c[0], 2 * y - prev_c[1]) if prev_c else (x, y)
                p = [c1] + [(x + a[k], y + a[k + 1]) if rel else (a[k], a[k + 1]) for k in (0, 2)]
            out.append('<curve x1="{}" y1="{}" x2="{}" y2="{}" x3="{}" y3="{}"/>'.format(*[_f(v) for q in p for v in q]))
            prev_c, prev_q = p[1], None
            x, y = p[2]
        elif C in "QT":
            if C == "Q":
                p = [(x + a[k], y + a[k + 1]) if rel else (a[k], a[k + 1]) for k in (0, 2)]
            else:
                c1 = (2 * x - prev_q[0], 2 * y - prev_q[1]) if prev_q else (x, y)
                p = [c1, (x + a[0], y + a[1]) if rel else (a[0], a[1])]
            out.append('<quad x1="{}" y1="{}" x2="{}" y2="{}"/>'.format(*[_f(v) for q in p for v in q]))
            prev_q, prev_c = p[0], None
            x, y = p[1]
        else:  # A
            x, y = (x + a[5], y + a[6]) if rel else (a[5], a[6])
            out.append(f'<arc rx="{_f(a[0])}" ry="{_f(a[1])}" x-axis-rotation="{_f(a[2])}" '
                       f'large-arc-flag="{int(a[3])}" sweep-flag="{int(a[4])}" x="{_f(x)}" y="{_f(y)}"/>')
            prev_c = prev_q = None
    return "<path>" + "".join(out) + "</path>"


def stencil_xml(svg: str) -> str:
    raiz = ET.fromstring(svg)
    _, _, w, h = (float(v) for v in raiz.get("viewBox").split())
    partes, color = [], None
    for el in raiz.iter():
        if el.tag in (NS + "svg", NS + "g", NS + "defs"):
            continue
        if el.tag != NS + "path" or el.get("transform") or el.get("fill-rule"):
            raise ValueError(f"elemento no soportado: {el.tag} {el.attrib}")
        fill, stroke = el.get("fill", "#000"), el.get("stroke")
        if fill != "none" and fill != color:  # solo cuando cambia: casi todos alternan dos colores
            partes.append(f'<fillcolor color="{fill}"/>')
            color = fill
        if stroke:
            partes.append(f'<strokecolor color="{stroke}"/><strokewidth width="{el.get("stroke-width", "1")}"/>')
            if el.get("stroke-miterlimit"):
                partes.append(f'<miterlimit limit="{el.get("stroke-miterlimit")}"/>')
        partes.append(_path(el.get("d")))
        partes.append("<fillstroke/>" if stroke and fill != "none" else "<stroke/>" if stroke else "<fill/>")
    return (f'<shape w="{_f(w)}" h="{_f(h)}" aspect="fixed"><foreground>'
            + "".join(partes) + "</foreground></shape>")


def comprimir(xml: str) -> str:
    """Como `Graph.compress` de draw.io: deflate crudo y base64. Sin `encodeURIComponent`, que no
    hace falta porque el XML no trae `%` y `decodeURIComponent` lo deja igual."""
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return base64.b64encode(c.compress(xml.encode("utf-8")) + c.flush()).decode()


def stencil(svg: str) -> str:
    return comprimir(stencil_xml(svg))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(stencil(open(sys.argv[1], encoding="utf-8").read()))
