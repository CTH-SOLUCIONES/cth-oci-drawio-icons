---
name: oci-drawio-diagrams
description: Draws architecture diagrams of Oracle Cloud Infrastructure (OCI) in draw.io with Oracle's official icons from the OCI Architecture Diagram Toolkit v24.2, shipped as inline stencils so they show in the draw.io MCP viewer. Includes an icon and container catalog with a search script, an embed script that makes the file self-contained, and layout rules verified by rendering. Use it whenever someone asks to diagram, draw or document an architecture on OCI or Oracle Cloud, for example a VCN with subnets, OKE, Autonomous Database, Object Storage or an API Gateway.
license: MIT for the skill's text and scripts. The icons, and the stencils derived from them in catalog.json, are © Oracle and are not covered; see NOTICE.md in the repository.
compatibility: Python 3.10+. Works best with the draw.io MCP server; without it, write the .drawio file directly with the same styles. draw.io desktop is optional, for the render check.
metadata:
  author: CTH Soluciones Tecnológicas
  version: "24.2.5"
---

# OCI architecture diagrams with the official icons

The icons are the ones in Oracle's **OCI Architecture Diagram Toolkit v24.2**, published in the
repository `CTH-SOLUCIONES/cth-oci-drawio-icons`. In the XML sent to the MCP they go **inline, as
draw.io stencils** (`shape=stencil(…)`): vector, compressed, and with no external image. They don't
show if loaded by URL, because the chat viewer only loads images from diagrams.net domains. Before
delivering, **always embed** them with the script, which makes them canonical. Never use generic
shapes or the "OCI Icons" set that draw.io itself ships: those are not the official icons.

This skill carries the catalog, with the 232 icons as stencils, and the scripts. Paths are relative to
this skill's folder, so it works offline and without cloning anything.

## 1. Find the icons and the containers

Don't read `catalog.json` in full (it is about 700 KB). Search it:

```bash
python3 scripts/search.py kubernetes          # slug | label | category | width x height
python3 scripts/search.py --style vault waf   # inline style, ready to paste, and the running total
python3 scripts/search.py --containers        # region, AD, VCN, subnet… with their style
```

Search in English, which is the language of Oracle's labels. Don't guess a slug. These are the most
used:

| Service | slug | Service | slug |
|---|---|---|---|
| OKE | `container-engine-for-kubernetes` | Load Balancer | `load-balancer` |
| Container Registry | `container-registry` | API Gateway | `api-gateway` |
| Autonomous Database | `oracle-autonomous-database` | WAF | `waf` |
| Base Database | `oracle-base-database` | Bastion | `bastion` |
| Object Storage | `object-storage-buckets` | DRG | `drg` |
| Block / File Storage | `block-storage` / `file-storage` | Internet / NAT / Service Gateway | `internet-gateway` / `nat-gateway` / `service-gateway` |
| Vault | `vault` | NSG | `nsg` |
| Key Management | `key-management` | IAM | `iam` |
| Functions | `functions` | DNS | `dns` |
| Streaming / Queue | `streaming` / `queue` | Logging / Monitoring | `logging` / `monitoring` |
| Generative AI | `generative-ai` | Notifications / Events | `notifications` / `events` |
| Document Understanding | `document-understanding` | Vision | `vision` |
| VM | `virtual-machine` | User | `user` |

There are ten containers: `region`, `availability-domain`, `fault-domain`, `tenancy`, `compartment`,
`vcn`, `subnet`, `oke-cluster`, `on-premises` and `internet`.

If a service has no icon in the catalog, say so. Anything that isn't OCI (another cloud, the user's
phone, a customer's system) goes as a neutral shape with its name.

## 2. Build the diagram in the draw.io MCP

- Use `create_diagram` in `xml` format, with `routing: "libavoid"`.
- **Icon.** Write it as `<mxCell value="<label>" style="<style>" vertex="1" parent="1">`, with the
  catalog's `width` and `height`. The label goes in `value`, and the style already places it under the
  icon.
- **Copy the style from `--style` whole and untouched**, including the `ociIcon=<slug>` key, which is
  how the script identifies the icon when it embeds. Ask for the style once per service and repeat it
  in every cell that uses it.
- **Budget: the whole XML under 20,000 characters.** `create_diagram` returns the entire XML and,
  after it, a link to the draw.io editor with the diagram compressed inside. With stencils that link is
  about 85 % as long as the XML, so the result is close to twice the XML, and the client cuts results over
  25,000 tokens. A physical view with 10 icons (27,426 characters of XML) came back as a 53,883-character
  result and the viewer received nothing; one with 7 icons (21,176 characters) showed. An icon's style
  weighs from about 0.8 to 8.6 KB, so count with `--style`, which sums what you asked for and warns if it doesn't fit; every cell that
  repeats an icon adds to the total again.
- **If it doesn't fit**, split the diagram into views (physical and logical, or one per layer) or use
  `--url` for the icons. `--url` costs about 300 characters per icon, but the viewer shows the icon
  empty: tell the person they will see it when they open the file in draw.io, and embed anyway before
  delivering.
- **Container.** It carries its style and the label in `value`. Write the containers **before** the
  icons so they end up behind, in this order: region → VCN → subnet.
- The toolkit's "Logical" and "Physical" pages set the convention. The physical view has region, AD,
  VCN and subnets. The logical view has layers and flows, with no network topology.
- If the draw.io MCP isn't connected, say so before going on. Then write the `.drawio` file directly,
  with the same styles and rules.

## 3. Layout rules

The chat viewer applies `libavoid`, but **the saved XML keeps draw.io's default routing**. The diagram
has to look right that way too. These rules were verified by rendering with the default routing:

- **Flow goes left to right.** The entry point (user, internet, WAF) is on the left and the data and
  services are on the right. Use a grid of 10. Leave at least 200 px between columns of icons and
  90 px between rows, so the label and the trunk of the arrows fit.
- **Every arrow declares where it leaves and where it enters.** It leaves on the right and enters on
  the left. If you don't declare it, draw.io enters the targets from the top or the bottom, merges
  several arrows into one line that crosses icons, and leaves below the icon, on top of its label.
  This is the style:
  `edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;endArrow=block;strokeColor=#312D2A;exitX=1;exitY=0.5;exitDx=0;exitDy=0;entryX=0;entryY=0.5;entryDx=0;entryDy=0;`
- **Align the centers of each row** with `y = row_center − height/2`. Icons don't all have the same
  size, so aligning only the top edge gives horizontal arrows a step.
- **If a node fans out to several, stack the targets in one column.** With the ports on the sides,
  draw.io builds a vertical trunk between the two columns without touching any icon.
- **Nothing leaves from below an icon**, because its label is there. No arrow should run down through
  a container's label either, which sits at the top left.
- **Keep container borders away from each arrow's midpoint.** For an arrow from A to B, take
  x = (A's right edge + B's left edge) / 2. A bent arrow runs its vertical segment at x, and a straight
  arrow's label is centered at x, so a border at x puts the line or the label on top of it. Between
  two sibling containers, center their gap on x. A single border in the way (a VCN's or the region's)
  goes at the 40 px margin from the nearer icon, which the 200 px column spacing keeps clear of x.
- **A container's bottom margin must count the icon's label.** Leave at least 60 px between the bottom
  edge of the lowest icon and the container's edge. The other margins are 40 px.
- Put text on an arrow only when it clarifies the protocol or the flow.

## 4. Save and deliver

1. Save the XML as a `.drawio` file, wrapped in `<mxfile><diagram name="…">…</diagram></mxfile>`.
   Put it in the project folder or, in claude.ai, as a downloadable file.
2. **Always embed** with `python3 scripts/embed.py diagram.drawio`, even if the icons are already
   inline. The script puts the catalog's canonical stencil in every cell with `ociIcon`, without a
   network, and leaves a `.bak`. It keeps whatever else the cell has, such as the font size. That
   fixes any mistranscribed copy and swaps URLs for the stencil, so the deliverable is self-contained.
3. **Check the result before delivering it.**
   - If draw.io desktop is installed, render and open the PNG. On macOS:
     `/Applications/draw.io.app/Contents/MacOS/draw.io -x -f png -s 2 -o review.png diagram.drawio`.
     On Linux, the same command with `drawio`.
   - Without draw.io desktop, the check is the MCP viewer.
   - If an arrow crosses a label or an icon, fix the position according to section 3.

## Ownership

The icons are © Oracle, published to draw diagrams of OCI implementations. Use them only for that. The
repository grants no license on them; see its `NOTICE.md`.
