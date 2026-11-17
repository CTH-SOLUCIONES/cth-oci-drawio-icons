#!/usr/bin/env python3
"""Make the OCI icons of a .drawio canonical and inline, so the deliverable depends on no URL.

Each icon in the catalog carries `ociIcon=<slug>` in its style. In every cell with that key, this
script writes the catalog's canonical form: the inline stencil (`shape=stencil(...)`). It does not
matter whether the icon arrived as a URL, as a stencil or as an inline image from an earlier
version. If the agent mistyped a stencil, it gets corrected. The cell's other style keys are kept.
Cells from diagrams that predate `ociIcon` are recognized by their CDN URL.

Everything comes from `catalog.json`, with no network. If the diagram uses icons from another
toolkit, they are downloaded and left as an inline image.

Usage:
  embed.py diagram.drawio                # writes the embedded diagram in place (keeps a .bak)
  embed.py diagram.drawio output.drawio
"""
import base64
import functools
import json
import re
import sys
import urllib.parse
import urllib.request
import zlib
from pathlib import Path

CATALOG = Path(__file__).resolve().parent.parent / "catalog.json"
ICON_URL = re.compile(
    r"https://cdn\.jsdelivr\.net/gh/CTH-SOLUCIONES/cth-oci-drawio-icons@([^/]+)/svg/([a-z0-9-]+)\.svg")
# Keys the canonical form sets itself, or that stop applying once the shape is a stencil.
DROPPED_KEYS = {"shape", "image", "imageAspect"}

StylePairs = list[tuple[str, str | None]]


def _toolkit_of(version: str) -> str:
    """`v24.2.3` -> `v24.2`: this repo's revisions do not change the drawing."""
    return version.rsplit(".", 1)[0]


@functools.cache
def _load_catalog() -> tuple[str, dict[str, str]]:
    """The catalog version and the canonical inline style of each icon, by slug."""
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    return catalog["version"], {i["slug"]: i["style"] for i in catalog["icons"]}


def _style_pairs(style: str) -> StylePairs:
    """The style as an ordered list of (key, value); the value is `None` for entries without `=`, like `ellipse`."""
    pairs: StylePairs = []
    for part in style.split(";"):
        if part:
            key, separator, value = part.partition("=")
            pairs.append((key, value if separator else None))
    return pairs


def _join(pairs: StylePairs, values: dict[str, str | None]) -> str:
    """Serialize pairs back to a style string, taking each value from `values`; `None` means a bare key."""
    return ";".join(k if v is None else f"{k}={values.get(k, v)}" for k, v in pairs) + ";"


def _canonical_style(style: str, count: dict) -> str:
    """Rewrite one cell style to its canonical form. `count` accumulates `total` and `missing` slugs."""
    pairs = _style_pairs(style)
    values = dict(pairs)
    image = values.get("image") if (values.get("image") or "").startswith("https://") else None
    url_match = ICON_URL.fullmatch(image or "")
    slug = values.get("ociIcon") or (url_match.group(2) if url_match else None)
    if slug is None:
        return style
    version, icons = _load_catalog()
    if url_match is not None and _toolkit_of(url_match.group(1)) != _toolkit_of(version):  # icons from another toolkit
        with urllib.request.urlopen(image, timeout=30) as response:
            count["total"] += 1
            # draw.io uses `data:<type>,<base64>` without `;base64`: the `;` separates style keys.
            values["image"] = "data:image/svg+xml," + base64.b64encode(response.read()).decode()
            return _join(pairs, values)
    canonical = icons.get(slug)
    if canonical is None:
        count["missing"].append(slug)
        return style
    count["total"] += 1
    canonical_pairs = _style_pairs(canonical)
    canonical_keys = {k for k, _ in canonical_pairs}
    # The canonical form first; then what the cell added or changed (font size, position...).
    extra = [(k, v) for k, v in pairs if k not in DROPPED_KEYS and k not in canonical_keys]
    overrides = {k: v for k, v in pairs if k in canonical_keys and k not in DROPPED_KEYS}
    return _join(canonical_pairs + extra, overrides)


def _inflate(content: str) -> str:
    """Decode the body of a compressed `<diagram>`: base64, raw deflate, URL-encoded XML."""
    return urllib.parse.unquote(zlib.decompress(base64.b64decode(content), -15).decode())


def embed(text: str) -> tuple[str, dict]:
    """Return the file with canonical icons, and the count. Compressed diagrams are
    decompressed: draw.io opens plain XML just the same."""
    count = {"total": 0, "missing": []}

    def rewrite_styles(xml: str) -> str:
        return re.sub(r'style="([^"]*)"', lambda m: 'style="' + _canonical_style(m.group(1), count) + '"', xml)

    def rewrite_diagram(match: re.Match) -> str:
        opening, body, closing = match.group(1), match.group(2), match.group(3)
        if body.strip() and not body.strip().startswith("<"):
            body = _inflate(body.strip())
        return opening + rewrite_styles(body) + closing

    if "<diagram" in text:
        text = re.sub(r"(<diagram[^>]*>)(.*?)(</diagram>)", rewrite_diagram, text, flags=re.S)
    else:  # bare XML, like the one the MCP receives
        text = rewrite_styles(text)
    return text, count


def main(args: list[str]) -> None:
    if len(args) not in (1, 2):
        sys.exit(__doc__)
    source = Path(args[0])
    target = Path(args[1]) if len(args) == 2 else source
    original = source.read_text(encoding="utf-8")
    text, count = embed(original)
    if target == source:
        source.with_suffix(source.suffix + ".bak").write_text(original, encoding="utf-8")
    target.write_text(text, encoding="utf-8")
    remaining_urls = len(re.findall(r"image=https?://", text))
    print(f"{count['total']} icons embedded in {target}"
          + (f"; not in the catalog: {', '.join(sorted(set(count['missing'])))}" if count["missing"] else "")
          + (f"; {remaining_urls} URL images remain that are not from this repository" if remaining_urls else ""))


if __name__ == "__main__":
    main(sys.argv[1:])
