## What changes

<!-- One or two sentences. Which file, which icon or which rule. -->

## Evidence

<!-- A new or changed layout rule: attach the PNG that draw.io rendered from the saved XML, with its
default routing, and say the draw.io version. An icon fix: the slug and the toolkit page where the
icon appears. A script fix: the test that fails without it. -->

## Checklist

- [ ] Layout rules I added or changed were verified by rendering the saved XML with draw.io's default routing (PNG attached).
- [ ] Icons come only from Oracle's official toolkit; I added none from other sources.
- [ ] `python3 -m unittest discover -s tests` passes.
- [ ] I ran `python3 scripts/package.py` and committed the synced skill copy (`--check` is clean).
- [ ] I added a line under `## Unreleased` in CHANGELOG.md.
