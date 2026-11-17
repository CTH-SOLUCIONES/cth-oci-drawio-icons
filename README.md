# cth-oci-drawio-icons

An [Agent Skill](https://agentskills.io) and an icon set for drawing Oracle Cloud Infrastructure (OCI)
architecture diagrams in draw.io. It carries the 232 icons of Oracle's **OCI Architecture Diagram
Toolkit v24.2** as draw.io stencils, a catalog to search them, and the layout rules that keep an
agent's diagrams readable.

**Audience:** anyone who draws OCI architectures in draw.io, whether a person or a coding or chat
agent that uses the draw.io MCP server.

> **The icons belong to Oracle.** Oracle publishes them to draw diagrams of OCI implementations and
> does not grant permission to redistribute them. This repository grants no license on them, is not
> affiliated with Oracle, and will remove them if Oracle asks. See [Icon ownership](#icon-ownership)
> and [NOTICE.md](NOTICE.md).

## Why it exists

Three constraints shape how the icons are packaged.

1. **Size.** The toolkit's icons are groups of vector shapes of 5 to 20 KB each. Put inside a diagram's
   XML, a real physical view weighs 150 to 200 KB, too much to write in one call to the MCP.
2. **The result limit.** `create_diagram` returns the whole XML, and the client cuts results over
   25,000 tokens. A diagram of about 50 KB (53,638 characters, with base64 SVGs) reached the viewer as
   a notice instead of the diagram.
3. **The viewer's content policy.** The draw.io MCP viewer only loads images from diagrams.net
   domains and `data:` URIs. Icons referenced by CDN URL render empty in the chat viewer, although
   draw.io itself opens them.

The answer is to ship each icon as a **draw.io stencil** (`shape=stencil(…)`) that goes inline in the
style. It is vector and compressed: the most used icons weigh 1.4 KB at the median, 37 % less than
the same icon as base64 SVG, and a physical view of 9 icons went from 33,563 to 24,118 characters. The
skill keeps the whole XML under 30,000 characters. That budget is a criterion derived from the failure
above, not a measured limit.

The "OCI Icons" set that draw.io ships doesn't solve it: it is generic black glyphs, and services such
as Autonomous Database, Object Storage, Vault or OKE don't exist in it by name.

How the icons were made: exported with draw.io from the toolkit without redrawing them, slimmed
with SVGO, and converted to stencils with absolute coordinates at 0.1 px. Relative coordinates at that
precision deformed the DRG ring.

## What's inside

| Path | Content |
|---|---|
| [`skills/oci-drawio-diagrams/`](skills/oci-drawio-diagrams/SKILL.md) | The skill, self-contained: how to search the icons, build the diagram in the MCP, the layout rules verified by rendering, and how to deliver. It carries its own `catalog.json` and two scripts (`search.py`, `embed.py`) |
| `svg/<slug>.svg` | The 232 icons, one SVG each, exported from the toolkit's "Icons" page |
| `catalog.json` | Per icon: `slug`, `label`, `category`, `width`, `height`, `file`, `style` (the inline stencil) and `url_style` (the CDN URL). Also 10 physical-view containers (region, availability domain, fault domain, tenancy, compartment, VCN, subnet, OKE cluster, on-premises, internet) with the style from the toolkit's legend |
| `catalog.md` | The same list, readable, by category |
| `scripts/search.py` | Searches the catalog without loading it whole. `--style` gives the inline style and sums it against the 30,000-character budget; `--url` gives the CDN style; `--containers` lists the containers |
| `scripts/embed.py` | Replaces every icon in a `.drawio` file with its canonical stencil, keeping the rest of the cell's style |
| `scripts/package.py` | Syncs the skill's copy of the catalog and scripts, and builds `dist/oci-drawio-diagrams.zip`. With `--check` it fails if the copy differs from the root |
| `scripts/extract.py`, `optimize.py`, `stencil.py` | Regenerate everything from a new toolkit. `extract.py` calls the other two |
| `tests/` | Tests for the scripts, standard library only |

## Install

**Any agent that supports skills** (Claude Code, Codex, Gemini CLI, Cursor, GitHub Copilot and others),
with the [`skills`](https://github.com/vercel-labs/skills) CLI:

```sh
npx skills add CTH-SOLUCIONES/cth-oci-drawio-icons        # current project
npx skills add CTH-SOLUCIONES/cth-oci-drawio-icons -g     # every project (global)
```

**Claude Code**, as a plugin:

```
/plugin marketplace add CTH-SOLUCIONES/cth-oci-drawio-icons
/plugin install oci-drawio-diagrams@cth-oci-drawio-icons
```

**A Claude organization**, by uploading the zip. The skill is self-contained for this reason: in
claude.ai, code execution by default only reaches package registries, not the CDN, and the skill
upload rejects zips of more than 200 files. The icons therefore live inside the catalog, as stencils,
and not one per file.

1. Build the zip with `python3 scripts/package.py`. It writes `dist/oci-drawio-diagrams.zip`, and
   `dist/` is not versioned.
2. The organization's owner uploads it in *Organization settings > Plugins & skills > Add > Upload a
   skill*. The skill is then active for every member in claude.ai, Claude Desktop, Cowork and Claude
   Code signed in to the organization. Members can turn it off but not delete it.
3. The *Policy* tab must have *Cloud code execution and file creation* and *Skills* enabled.
4. To design, each member also needs the draw.io connector.

**By hand:** copy `skills/oci-drawio-diagrams/` into your agent's skills folder, for example
`~/.claude/skills/oci-drawio-diagrams/` for Claude Code.

The scripts need Python 3.10 or later and nothing else. Diagrams are drawn through the draw.io MCP
server when it is connected; without it, the skill writes the `.drawio` file directly.

## Use

The skill activates when you ask for a diagram of an architecture on OCI. You can also ask for it
directly:

- "Draw the physical view of a VCN with a public subnet for the load balancer and a private one for
  OKE, using the OCI icons."
- "Make a logical diagram of an API Gateway in front of Functions that read from Autonomous Database
  and Object Storage."
- "Add a WAF and a bastion to this `.drawio` and embed the icons again."

The agent searches the catalog, writes the XML with each icon's inline style, saves a `.drawio` file,
and runs `embed.py` on it before delivering. You can run the same steps by hand:

```sh
python3 skills/oci-drawio-diagrams/scripts/search.py --style vault waf    # inline style and total
python3 skills/oci-drawio-diagrams/scripts/embed.py diagram.drawio        # in place, leaves a .bak
python3 skills/oci-drawio-diagrams/scripts/embed.py diagram.drawio out.drawio
```

Every icon style carries `ociIcon=<slug>`, a key draw.io keeps and that identifies the icon even when
the image is inline. `embed.py` uses it to replace each icon with the canonical stencil, which fixes
mistranscribed copies and swaps URL-mode icons for the stencil. The deliverable then depends on no URL
and no network.

## URL mode and the CDN

`search.py --url <slug>` gives a style that references the icon by URL. It costs about 300 characters
per icon instead of 1.4 KB, so it helps when a diagram doesn't fit the budget. The price is that the
MCP viewer shows those icons empty, while draw.io shows them. Run `embed.py` before delivering.

The URL is pinned to a tag:

```
https://cdn.jsdelivr.net/gh/CTH-SOLUCIONES/cth-oci-drawio-icons@v24.2.4/svg/<slug>.svg
```

It goes through jsDelivr and not through raw GitHub URLs, because those are served as `text/plain`.
The tag also fixes the version: `v24.2.4` is the toolkit 24.2 in revision 4 of this repository. When
another version comes out, old diagrams keep pointing at their own tag.

Revisions change the encoding, never the drawing. The [changelog](CHANGELOG.md) has the detail; in
short:

- v24.2 was withdrawn: adaptive colors turned the icons' interiors black in dark viewers, and jsDelivr
  caches a tag forever, so it couldn't be fixed in place.
- v24.2.1 shipped unoptimized SVGs.
- v24.2.2 inlined them as base64 SVG, which overflowed the MCP result.
- v24.2.3 moved to stencils.
- v24.2.4 is the English rename and the public release.

## Regenerating from a new toolkit

When Oracle publishes a new version of the toolkit, `scripts/extract.py` rebuilds `svg/`,
`catalog.json` and `catalog.md` from the toolkit's `.drawio` file. It needs:

- The path to the toolkit file, in the `OCI_TOOLKIT` environment variable or as the first argument.
- The draw.io desktop binary, in `DRAWIO_BIN`. The default is
  `/Applications/draw.io.app/Contents/MacOS/draw.io`.
- Node, because the script runs `npx svgo@4.1.0`.

Then run `python3 scripts/package.py` to sync the skill's copy and build the zip. CI fails if the copy
and the root differ. [CONTRIBUTING.md](CONTRIBUTING.md) covers the version number.

## Scope and limits

- **In scope:** the 232 icons and 10 containers of toolkit 24.2, the search and embed scripts, and the
  layout rules in the skill.
- **Not in scope:** icons that aren't in Oracle's toolkit, in other styles or for other clouds. Anything
  that isn't OCI is drawn as a neutral shape. The skill says so when a service has no icon.
- **Layout rules are for the default routing.** The chat viewer applies its own routing (`libavoid`),
  but the saved XML keeps draw.io's default one. The rules were verified by rendering with the default
  one. They don't promise a good layout for every diagram, and the skill asks for a render check before
  delivery when draw.io desktop is available.
- **The 30,000-character budget** comes from one observed failure, not from a documented limit of the
  client.
- **The draw.io MCP server gives the best result.** Without it, the agent writes the `.drawio` file
  directly, and you check the render in draw.io.
- **Python 3.10 or later.**

## Icon ownership

The icons are **Oracle's** (© Oracle and/or its affiliates). They come from the toolkit that Oracle
publishes in its
[documentation](https://docs.oracle.com/en-us/iaas/Content/General/Reference/graphicsfordiagrams.htm)
to draw architecture diagrams of OCI implementations. This repository only reorganizes them for that
use: one file per icon, a searchable catalog, and draw.io stencils. The icons are not redrawn: the
conversion rounds coordinates (SVGO to 0.01 px, stencils to 0.1 px), with no visible difference when
rendered.

- Oracle does not grant redistribution of the icons, and this repository grants no license on them.
  The same goes for the stencils derived from them in `catalog.json` and in the skill's copy.
- If Oracle asks for them to be removed, they will be removed.
- CTH Soluciones Tecnológicas is not affiliated with Oracle.

If you need certainty about your use of the icons, check Oracle's terms. [NOTICE.md](NOTICE.md) has
the details.

## Contributing

Issues and pull requests are welcome: missing or misnamed icons, layout rules, script fixes and new
toolkit versions. A layout rule has to be verified by rendering the saved XML with draw.io's default
routing, with the PNG attached. Read [CONTRIBUTING.md](CONTRIBUTING.md) before you open a pull
request.

## License

The text and the scripts are [MIT](LICENSE) © 2026 CTH Soluciones Tecnológicas. The icons in `svg/`,
and the stencils derived from them, are not covered by that license; see [NOTICE.md](NOTICE.md).
