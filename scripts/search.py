#!/usr/bin/env python3
"""Search the OCI icon catalog and print an icon's style, without loading the whole catalog into the agent's context.

Usage:
  search.py <term> [<term>...]   # matches slug, label or category, ignoring accents and case
  search.py --style <slug>...    # inline style (stencil): renders in the draw.io MCP viewer
  search.py --url <slug>...      # URL style: lightweight, but the MCP viewer does not render it
  search.py --containers         # the 10 containers of the physical view, with their style

With --style, the last line adds up the size of the requested styles against the XML budget.
"""
import json
import sys
import unicodedata
from pathlib import Path

CATALOG = Path(__file__).resolve().parent.parent / "catalog.json"
# `create_diagram` returns the whole XML plus an editor link with the diagram compressed inside; with
# stencils the result is close to twice the XML, and the client cuts tool results above 25,000 tokens. Measured on
# 2026-11-16: 27,426 characters of XML did not reach the viewer, 21,176 did. 20,000 leaves a margin.
BUDGET = 20_000
BUDGET_WARNING_RATIO = 0.8


def _normalize(text: str) -> str:
    """Lowercase and strip accents, so `Catálogo` matches `catalogo`."""
    decomposed = unicodedata.normalize("NFD", text.lower())
    return "".join(c for c in decomposed if unicodedata.category(c) != "Mn")


def _print_containers(catalog: dict) -> None:
    for c in catalog["containers"]:
        print(f"{c['type']} | {c['label']} | {c['width']}x{c['height']} | {c['style']}")


def _print_styles(catalog: dict, flag: str, slugs: list[str]) -> None:
    by_slug = {i["slug"]: i for i in catalog["icons"]}
    key = "style" if flag == "--style" else "url_style"
    total = 0
    for slug in slugs:
        icon = by_slug.get(slug)
        if icon is None:
            print(f"{slug} | not in the catalog")
            continue
        total += len(icon[key])
        print(f"{slug} | {icon['width']}x{icon['height']} | {icon[key]}")
    if key == "style":
        print(f"# {total} characters in styles (each cell that repeats an icon adds its own again); "
              f"the full XML must stay under {BUDGET}"
              + ("" if total < BUDGET * BUDGET_WARNING_RATIO
                 else ": it does not fit, use --url and warn that the viewer will not render the icons"))


def _print_matches(catalog: dict, terms: list[str]) -> None:
    wanted = [_normalize(t) for t in terms]
    found = [i for i in catalog["icons"]
             if all(t in _normalize(f"{i['slug']} {i['label']} {i['category']}") for t in wanted)]
    for i in found:
        print(f"{i['slug']} | {i['label']} | {i['category']} | {i['width']}x{i['height']}")
    if not found:
        print("no matches: try fewer words or another term")


def main(args: list[str]) -> None:
    if not args:
        sys.exit(__doc__)
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    if args[0] == "--containers":
        _print_containers(catalog)
    elif args[0] in ("--style", "--url"):
        _print_styles(catalog, args[0], args[1:])
    else:
        _print_matches(catalog, args)


if __name__ == "__main__":
    main(sys.argv[1:])
