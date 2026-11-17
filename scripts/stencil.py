#!/usr/bin/env python3
"""Convert the icon SVGs into draw.io stencils: vector, compressed and with no external image.

The `create_diagram` response repeats the whole XML. With the icons as inline SVG (base64), a
medium-sized view exceeded the token cap the client allows for a tool result, and the viewer got
the error notice instead of the diagram. A compressed stencil (`shape=stencil(...)`) weighs 37 %
less on the most used icons, the viewer draws it without loading anything, and it is the same
format draw.io uses to save custom shapes. Coordinates are absolute and rounded to 0.1 px: no
accumulated error, as happened with SVGO's relative ones at that precision.

It only covers what these SVGs contain: `<path>` with `fill`, and a stroke with `stroke`, without
`transform` or `fill-rule`. If an SVG has anything else, it fails instead of drawing something
different.

Usage: stencil.py <file.svg>   # prints the value of `shape=stencil(...)`
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
    """Commands and numbers of a `d` attribute, honoring the arc flags that SVGO packs together
    (`a2 2 0 012 2` is flags 0 and 1 followed by 2)."""
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
            yield c  # arc flag: a single character
            i += 1
        else:
            m = _NUM.match(d, i)
            if not m:
                raise ValueError(f"cannot parse {d[i:i + 20]!r}")
            yield m.group()
            i = m.end()
        idx += 1


def _path(d: str) -> str:
    """Translate an SVG `d` into the path elements of a stencil, in absolute coordinates."""
    out, toks, x, y, sx, sy = [], list(_tokens(d)), 0.0, 0.0, 0.0, 0.0
    prev_c = prev_q = None  # last control point, for S and T
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
        arity = {"M": 2, "L": 2, "H": 1, "V": 1, "C": 6, "S": 4, "Q": 4, "T": 2, "A": 7}[C]
        a = [float(t) for t in toks[i:i + arity]]
        i += arity
        if C == "M":
            x, y = (x + a[0], y + a[1]) if rel else (a[0], a[1])
            sx, sy = x, y
            out.append(f'<move x="{_f(x)}" y="{_f(y)}"/>')
            cmd = "l" if rel else "L"  # pairs following an M are lines
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
    root = ET.fromstring(svg)
    _, _, w, h = (float(v) for v in root.get("viewBox").split())
    parts, color = [], None
    for el in root.iter():
        if el.tag in (NS + "svg", NS + "g", NS + "defs"):
            continue
        if el.tag != NS + "path" or el.get("transform") or el.get("fill-rule"):
            raise ValueError(f"unsupported element: {el.tag} {el.attrib}")
        fill, stroke = el.get("fill", "#000"), el.get("stroke")
        if fill != "none" and fill != color:  # only when it changes: almost all alternate two colors
            parts.append(f'<fillcolor color="{fill}"/>')
            color = fill
        if stroke:
            parts.append(f'<strokecolor color="{stroke}"/><strokewidth width="{el.get("stroke-width", "1")}"/>')
            if el.get("stroke-miterlimit"):
                parts.append(f'<miterlimit limit="{el.get("stroke-miterlimit")}"/>')
        parts.append(_path(el.get("d")))
        parts.append("<fillstroke/>" if stroke and fill != "none" else "<stroke/>" if stroke else "<fill/>")
    return (f'<shape w="{_f(w)}" h="{_f(h)}" aspect="fixed"><foreground>'
            + "".join(parts) + "</foreground></shape>")


def compress(xml: str) -> str:
    """Like draw.io's `Graph.compress`: raw deflate and base64. Without `encodeURIComponent`, which is
    not needed because the XML has no `%` and `decodeURIComponent` leaves it unchanged."""
    c = zlib.compressobj(9, zlib.DEFLATED, -15)
    return base64.b64encode(c.compress(xml.encode("utf-8")) + c.flush()).decode()


def stencil(svg: str) -> str:
    return compress(stencil_xml(svg))


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    print(stencil(open(sys.argv[1], encoding="utf-8").read()))
