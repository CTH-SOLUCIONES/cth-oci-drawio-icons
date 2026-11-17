# Changelog

All notable changes are listed here. Versions follow `v<toolkit>.<revision>`: the first two numbers
are the version of Oracle's OCI Architecture Diagram Toolkit the icons come from, and the last one is
the revision of this repository. A revision changes how the icons are encoded or how the skill
works, never the drawings.

## Unreleased

## 24.2.4 — 2026-11-16

First public release. Same icons as 24.2.3, with the repository prepared for others to use.

- Everything is in English: the skill (`oci-drawio-diagrams`, previously `diagramas-oci`), the
  catalog keys, the scripts and their command-line interface, and the documentation.
- Catalog and scripts renamed: `catalogo.json` to `catalog.json`, `buscar.py` to `search.py`,
  `embeber.py` to `embed.py`, `empaquetar.py` to `package.py`, `extraer.py` to `extract.py`,
  `optimizar.py` to `optimize.py`. The skill zip is now `dist/oci-drawio-diagrams.zip`.
- `package.py --check` fails when the skill's copy differs from the repository root.
- Tests for the scripts, with the standard library only (`python3 -m unittest discover -s tests`).
- Claude Code plugin and marketplace manifests, GitHub Actions validation, contribution guide, code
  of conduct, issue forms, pull request template and `LICENSE`. `NOTICE.md` already existed; it is
  translated.
- The CDN URLs now point at `@v24.2.4`. Diagrams that point at an older tag keep working.

## 24.2.3 — 2026-09-24

- Icons ship as draw.io stencils (`shape=stencil(...)`) with absolute coordinates at 0.1 px. Relative
  coordinates at that precision deformed the DRG ring.
- The most used icons weigh 1.4 KB at the median, 37 % less than the same icons as base64 SVG. A
  9-icon physical view went from 33,563 to 24,118 characters, which fits the draw.io MCP result.
- `embeber.py` (now `embed.py`) replaces each icon with its canonical stencil, using the
  `ociIcon=<slug>` key every icon style carries.
- The skill stays self-contained: it now carries its own catalog (icons as stencils) and scripts, in
  four files, to fit claude.ai's limit of 200 files per uploaded skill.

## 24.2.2 — 2026-09-24

- First release with the skill (`diagramas-oci`, now `oci-drawio-diagrams`): it carries its own
  catalog and scripts, with the icons bundled in one file (`iconos.json`) to fit claude.ai's limit
  of 200 files per uploaded skill, and layout rules verified by rendering.
- Icons were inlined as base64 SVG so they would show in the draw.io MCP viewer. A diagram of about
  50 KB (53,638 characters) overflowed the result limit of the client and reached the viewer as a
  notice instead of the diagram. Superseded by 24.2.3.

## 24.2.1 — 2026-09-24

- Icons as one SVG per icon, not optimized. Superseded by 24.2.2.

## 24.2 — withdrawn

Removed. Its icons used adaptive colors, which turned the interiors black in viewers with a dark
theme. jsDelivr caches a tag forever, so the fix could not reuse the tag: icons are now exported with
the light theme and the revision number is part of every tag from then on.
