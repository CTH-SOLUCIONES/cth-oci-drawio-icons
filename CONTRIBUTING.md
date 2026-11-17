# Contributing

Thanks for helping. A diagram skill is only useful if what it tells an agent to draw renders well, so a
contribution has to be checked against a real render, not just read.

Everyone who takes part follows the [Code of Conduct](CODE_OF_CONDUCT.md).

## What is welcome

- **Reports of a missing or misnamed icon.** Open an issue with the "Wrong or missing icon" form and
  say where the icon appears in Oracle's toolkit.
- **New layout rules for the skill**, when they come with evidence (see below).
- **Fixes to the scripts** in `scripts/`, with a test that fails without the fix.
- **A new version of Oracle's toolkit.** Regenerate the icons and catalog with `scripts/extract.py`
  and open a pull request. Open an issue first, so we agree on the version number.
- **A diagram that renders badly.** Open an issue with the "Diagram renders badly" form and attach
  the `.drawio` file and a PNG.

## What makes a change acceptable

1. **Layout rules are verified by rendering.** The rules in `SKILL.md` section 3 were checked by
   rendering the saved XML with draw.io's default routing, because the chat viewer applies its own
   routing but the saved file does not. A new or changed rule needs the PNG that draw.io produced from
   the saved XML, attached to the pull request, and the draw.io version. A rule that only looks right
   in the chat viewer is not enough.
2. **Icons come only from Oracle's official toolkit.** Don't add icons from other sources, redrawn
   icons, or icons for non-OCI products. The icons are Oracle's; see [NOTICE.md](NOTICE.md).
3. **Numbers stay sourced.** The 30,000-character budget is a criterion derived from one observed
   failure, not a measured limit; don't present it or any other figure as more than that. If you
   measure something, say how.
4. **Keep `SKILL.md` lean.** It is loaded every time the skill activates, and it has to stay under
   500 lines.

## How to propose a change

Fork the repo, make the change on a branch, and open a pull request. Fill in the template.

Before opening it, run these from the repository root. CI runs the same checks:

```sh
python3 -m unittest discover -s tests -v
python3 scripts/package.py            # syncs the skill copy and rebuilds the zip
python3 scripts/package.py --check    # fails if the skill copy differs from the root
pipx run --spec skills-ref==0.1.1 agentskills validate skills/oci-drawio-diagrams
```

The repository root is the source of truth. Edit `catalog.json` and `scripts/`, never the copies in
`skills/oci-drawio-diagrams/`; `package.py` overwrites them. `SKILL.md` lives only in the skill folder
and is edited there.

`scripts/extract.py` needs the toolkit's `.drawio` file (`OCI_TOOLKIT`, or its first argument), the
draw.io desktop binary (`DRAWIO_BIN`) and Node, for `npx svgo@4.1.0`. You don't need any of them to
change the docs, the skill or the other scripts.

## Versions and releases

Versions follow `v<toolkit>.<revision>`: `v24.2.4` is revision 4 of the icons from toolkit 24.2. A
new Oracle toolkit changes the first two numbers. A revision changes how the icons are
encoded or how the skill works, never the drawings.

The version appears in several places, and a release changes all of them together:

- the `VERSION` constant in `scripts/extract.py`, which writes `version`, `base_url` and every
  `url_style` (the CDN path ends in `@v<version>`) into `catalog.json`, and the header of
  `catalog.md`; `scripts/package.py` then copies `catalog.json` into the skill;
- `.claude-plugin/plugin.json`, and the plugin entry (and `metadata`, if it has one) of
  `.claude-plugin/marketplace.json`;
- `metadata.version` in the skill's `SKILL.md`;
- the CDN URLs in `README.md`;
- the top released entry of [CHANGELOG.md](CHANGELOG.md).

`tests/test_version.py` fails when any of them disagrees with `VERSION`. The maintainers do this when
they cut a release. Don't change them in your pull request; add a line under `## Unreleased` in
[CHANGELOG.md](CHANGELOG.md) instead.

Tags are never reused: jsDelivr caches a tag forever, so a fix always ships under a new revision.

## License

By contributing, you agree that your contribution to the text and code is licensed under the
[MIT License](LICENSE). The license does not cover the icons.
