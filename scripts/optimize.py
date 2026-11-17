#!/usr/bin/env python3
"""Slim down the SVGs that draw.io exports so they fit embedded in the MCP's XML.

The draw.io MCP viewer only loads images from diagrams.net or inline (`data:`), so for the icons to
show up in the chat they are embedded in the call, and every byte is written out. This script
removes what draw.io adds for its editor (cell ids, pointer-events, styles that repeat the
attribute, the canvas background) and then runs SVGO at 0.01 px precision (`-p 2`), which is
invisible in a 42 px icon.

Usage: optimize.py [folder]   # defaults to svg/, in place; requires npx (Node)
"""
import re
import subprocess
import sys
from pathlib import Path

SVGO = "svgo@4.1.0"  # pinned: another version may produce other bytes for the same icons


def clean(svg: str) -> str:
    svg = re.sub(r"<\?xml[^>]*\?>|<!DOCTYPE[^>]*>", "", svg)
    svg = re.sub(r'\s(?:data-cell-id|pointer-events)="[^"]*"', "", svg)
    # draw.io repeats fill and stroke in `style`; the attributes already carry them. Without the ids
    # and this, SVGO may merge strokes of the same color into one.
    svg = re.sub(r'\sstyle="(?:fill|stroke): [^"]*"', "", svg)
    return re.sub(r'(<svg[^>]*?)\sstyle="[^"]*"', r"\1", svg, count=1)  # canvas background and color-scheme


def main() -> None:
    folder = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / "svg"
    files = sorted(folder.glob("*.svg"))
    before = sum(f.stat().st_size for f in files)
    for f in files:
        f.write_text(clean(f.read_text(encoding="utf-8")), encoding="utf-8")
    subprocess.run(["npx", "-y", SVGO, "--multipass", "-p", "2", "-q", "-f", str(folder), "-o", str(folder)],
                   check=True)
    after = sum(f.stat().st_size for f in files)
    print(f"{len(files)} SVGs optimized: {before / 1e3:.0f} KB -> {after / 1e3:.0f} KB")


if __name__ == "__main__":
    main()
