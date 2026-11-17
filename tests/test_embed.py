"""embed.py: URL cells become canonical stencils, damaged stencils are repaired, other keys survive."""
import base64
import json
import re
import tempfile
import unittest
import urllib.parse
import zlib
from pathlib import Path
from unittest import mock

from support import load_catalog, run_main  # first: puts scripts/ on sys.path

import embed  # noqa: E402

CATALOG = load_catalog()
ICONS = {i["slug"]: i for i in CATALOG["icons"]}
VERSION = CATALOG["version"]
CDN = "https://cdn.jsdelivr.net/gh/CTH-SOLUCIONES/cth-oci-drawio-icons"
LEGACY = json.loads((Path(__file__).parent / "fixtures" / "legacy-styles.json").read_text(encoding="utf-8"))


def cell(style: str, cell_id: str = "2") -> str:
    return (f'<mxCell id="{cell_id}" value="x" style="{style}" vertex="1" parent="1">'
            f'<mxGeometry x="10" y="10" width="42" height="42" as="geometry"/></mxCell>')


def model(*cells: str) -> str:
    return ('<mxGraphModel><root><mxCell id="0"/><mxCell id="1" parent="0"/>' + "".join(cells)
            + "</root></mxGraphModel>")


def styles_of(xml: str) -> list[str]:
    return re.findall(r'style="([^"]*)"', xml)


def compress(xml: str) -> str:
    """What draw.io stores in a compressed `<diagram>`: URL-encode, raw deflate, base64."""
    packer = zlib.compressobj(9, zlib.DEFLATED, -15)
    raw = packer.compress(urllib.parse.quote(xml, safe="").encode()) + packer.flush()
    return base64.b64encode(raw).decode()


def stencil_payload(style: str) -> str:
    return re.match(r"shape=stencil\(([^)]*)\);", style).group(1)


class CanonicalFormTest(unittest.TestCase):
    def test_url_mode_cell_becomes_the_canonical_stencil(self):
        slug = "compute"
        out, count = embed.embed(model(cell(ICONS[slug]["url_style"])))
        self.assertEqual(styles_of(out)[-1], ICONS[slug]["style"])
        self.assertNotIn("image=http", out)
        self.assertEqual(count, {"total": 1, "missing": []})

    def test_cell_without_ociicon_is_recognized_by_its_cdn_url(self):
        # an older revision of this repo (same toolkit): no network, and no `ociIcon` in the style
        legacy = f"shape=image;imageAspect=0;image={CDN}@v24.2.1/svg/vault.svg;fontSize=9;"
        out, count = embed.embed(model(cell(legacy)))
        style = styles_of(out)[-1]
        self.assertEqual(stencil_payload(style), stencil_payload(ICONS["vault"]["style"]))
        self.assertIn("ociIcon=vault;", style)
        self.assertIn("fontSize=9;", style)
        self.assertEqual(count["total"], 1)

    def test_legacy_url_with_hyphens_and_digits_in_the_slug(self):
        for slug in ("container-engine-for-kubernetes", "generative-ai-2"):
            with self.subTest(slug=slug):
                legacy = f"shape=image;image={CDN}@v24.2.1/svg/{slug}.svg;"
                out, count = embed.embed(model(cell(legacy)))
                self.assertEqual(count["total"], 1)
                self.assertIn(f"ociIcon={slug};", styles_of(out)[-1])

    def test_truncated_stencil_is_replaced_by_the_canonical_one(self):
        canonical = ICONS["waf"]["style"]
        payload = stencil_payload(canonical)
        mangled = canonical.replace(payload, payload[: len(payload) // 2])
        self.assertNotEqual(mangled, canonical)
        out, _ = embed.embed(model(cell(mangled)))
        self.assertEqual(styles_of(out)[-1], canonical)

    def test_mangled_characters_in_the_stencil_are_replaced(self):
        canonical = ICONS["waf"]["style"]
        payload = stencil_payload(canonical)
        mangled = canonical.replace(payload, payload.replace("+", " ").replace("/", "_"))
        out, _ = embed.embed(model(cell(mangled)))
        self.assertEqual(styles_of(out)[-1], canonical)

    def test_other_style_keys_survive(self):
        canonical = ICONS["vault"]["style"]
        custom = canonical + "fillColor=#FF0000;fontSize=14;ellipse;"
        out, _ = embed.embed(model(cell(custom)))
        style = styles_of(out)[-1]
        pairs = embed._style_pairs(style)
        keys = [k for k, _ in pairs]
        self.assertEqual(dict(pairs)["fontSize"], "14")   # the cell's value wins over the canonical 11
        self.assertEqual(keys.count("fontSize"), 1)
        self.assertEqual(dict(pairs)["fillColor"], "#FF0000")
        self.assertIn("ellipse", keys)                    # a bare key is kept bare
        self.assertEqual(stencil_payload(style), stencil_payload(canonical))
        self.assertTrue(style.endswith(";"))

    def test_leftover_shape_and_image_keys_are_dropped(self):
        messy = ICONS["vault"]["url_style"] + ";imageAspect=1;shape=image;"
        out, _ = embed.embed(model(cell(messy)))
        style = styles_of(out)[-1]
        self.assertEqual(style.count("shape="), 1)
        self.assertNotIn("image=", style)
        self.assertNotIn("imageAspect", style)

    def test_cells_that_are_not_icons_are_untouched(self):
        edge = "edgeStyle=orthogonalEdgeStyle;rounded=0;html=1;"
        container = "whiteSpace=wrap;html=1;strokeWidth=2;dashed=1;"
        foreign = "shape=image;image=https://example.test/logo.svg;"
        xml = model(cell(edge, "3"), cell(container, "4"), cell(foreign, "5"))
        out, count = embed.embed(xml)
        self.assertEqual(out, xml)
        self.assertEqual(count, {"total": 0, "missing": []})

    def test_every_catalog_icon_survives_a_round_trip_from_its_url_form(self):
        cells = [cell(i["url_style"], str(n + 2)) for n, i in enumerate(CATALOG["icons"])]
        out, count = embed.embed(model(*cells))
        self.assertEqual(count["total"], len(CATALOG["icons"]))
        self.assertEqual(styles_of(out), [i["style"] for i in CATALOG["icons"]])


class UnknownIconTest(unittest.TestCase):
    def test_unknown_slug_is_counted_as_missing_and_left_alone(self):
        style = "shape=stencil(AAAA);ociIcon=not-an-oci-icon;fontSize=9;"
        out, count = embed.embed(model(cell(style)))
        self.assertEqual(count, {"total": 0, "missing": ["not-an-oci-icon"]})
        self.assertEqual(styles_of(out)[-1], style)

    def test_unknown_slug_is_named_in_the_cli_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "d.drawio"
            source.write_text(model(cell("ociIcon=ghost-icon;"), cell("ociIcon=ghost-icon;", "3"),
                                    cell(ICONS["vault"]["url_style"], "4")), encoding="utf-8")
            out, _, code = run_main(embed.main, [str(source), str(Path(tmp) / "out.drawio")])
        self.assertIsNone(code)
        self.assertIn("1 icons embedded", out)
        self.assertIn("not in the catalog: ghost-icon", out)
        self.assertEqual(out.count("ghost-icon"), 1)  # listed once, not once per cell


class CompressedDiagramTest(unittest.TestCase):
    def test_compressed_diagram_is_inflated_and_canonicalized(self):
        inner = model(cell(ICONS["compute"]["url_style"]))
        text = f'<mxfile host="app.diagrams.net"><diagram id="p1" name="Page-1">{compress(inner)}</diagram></mxfile>'
        out, count = embed.embed(text)
        self.assertEqual(count["total"], 1)
        self.assertIn("<mxGraphModel>", out)              # plain XML now
        self.assertNotIn(compress(inner), out)
        self.assertEqual(styles_of(out)[-1], ICONS["compute"]["style"])
        self.assertTrue(out.startswith('<mxfile host="app.diagrams.net"><diagram id="p1" name="Page-1">'))
        self.assertTrue(out.endswith("</diagram></mxfile>"))

    def test_plain_diagram_keeps_its_wrapper(self):
        inner = model(cell(ICONS["compute"]["url_style"]))
        out, _ = embed.embed(f'<mxfile><diagram name="A">{inner}</diagram></mxfile>')
        self.assertTrue(out.startswith('<mxfile><diagram name="A"><mxGraphModel>'))
        self.assertEqual(styles_of(out)[-1], ICONS["compute"]["style"])

    def test_pretty_printed_multi_line_diagram_is_handled(self):
        inner = model(cell(ICONS["compute"]["url_style"])).replace("><", ">\n  <")
        out, count = embed.embed(f'<mxfile>\n<diagram name="A">\n{inner}\n</diagram>\n</mxfile>\n')
        self.assertEqual(count["total"], 1)
        self.assertEqual(styles_of(out)[-1], ICONS["compute"]["style"])

    def test_each_page_of_a_multi_page_file_is_handled(self):
        a = compress(model(cell(ICONS["compute"]["url_style"])))
        b = model(cell(ICONS["vault"]["url_style"]))
        out, count = embed.embed(f'<mxfile><diagram name="A">{a}</diagram><diagram name="B">{b}</diagram></mxfile>')
        self.assertEqual(count["total"], 2)
        self.assertEqual(styles_of(out)[-2:], [ICONS["compute"]["style"], ICONS["vault"]["style"]])


class FileHandlingTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.dir = Path(tmp.name)
        self.original = model(cell(ICONS["compute"]["url_style"]))
        self.path = self.dir / "diagram.drawio"
        self.path.write_text(self.original, encoding="utf-8")

    def test_in_place_run_writes_a_bak_with_the_original(self):
        out, _, code = run_main(embed.main, [str(self.path)])
        self.assertIsNone(code)
        backup = self.dir / "diagram.drawio.bak"
        self.assertEqual(backup.read_text(encoding="utf-8"), self.original)
        self.assertEqual(styles_of(self.path.read_text(encoding="utf-8"))[-1], ICONS["compute"]["style"])
        self.assertIn(f"1 icons embedded in {self.path}", out)

    def test_explicit_output_leaves_the_input_alone_and_writes_no_bak(self):
        target = self.dir / "out.drawio"
        run_main(embed.main, [str(self.path), str(target)])
        self.assertEqual(self.path.read_text(encoding="utf-8"), self.original)
        self.assertFalse((self.dir / "diagram.drawio.bak").exists())
        self.assertEqual(styles_of(target.read_text(encoding="utf-8"))[-1], ICONS["compute"]["style"])

    def test_second_run_is_idempotent(self):
        run_main(embed.main, [str(self.path)])
        first = self.path.read_text(encoding="utf-8")
        out, _, _ = run_main(embed.main, [str(self.path)])
        self.assertEqual(self.path.read_text(encoding="utf-8"), first)
        self.assertIn("1 icons embedded", out)
        # the second .bak is the already-embedded file, not the first original
        self.assertEqual((self.dir / "diagram.drawio.bak").read_text(encoding="utf-8"), first)

    def test_idempotent_on_a_compressed_diagram_too(self):
        self.path.write_text(f'<mxfile><diagram name="A">{compress(self.original)}</diagram></mxfile>',
                             encoding="utf-8")
        once, _ = embed.embed(self.path.read_text(encoding="utf-8"))
        twice, _ = embed.embed(once)
        self.assertEqual(once, twice)

    def test_wrong_number_of_arguments_exits_with_usage(self):
        _, _, code = run_main(embed.main, [])
        self.assertIn("Usage:", code)
        _, _, code = run_main(embed.main, ["a", "b", "c"])
        self.assertIn("Usage:", code)


class ToolkitComparisonTest(unittest.TestCase):
    def test_toolkit_is_the_version_without_the_revision(self):
        self.assertEqual(embed._toolkit_of("v24.2.3"), "v24.2")
        self.assertEqual(embed._toolkit_of(VERSION), "v24.2")

    def test_a_url_from_the_same_toolkit_never_touches_the_network(self):
        def forbidden(*args, **kwargs):
            raise AssertionError("network access")

        original = embed.urllib.request.urlopen
        embed.urllib.request.urlopen = forbidden
        self.addCleanup(setattr, embed.urllib.request, "urlopen", original)
        for revision in ("v24.2.0", VERSION, "v24.2.99"):
            embed.embed(model(cell(f"shape=image;image={CDN}@{revision}/svg/vault.svg;")))


class OtherToolkitDownloadTest(unittest.TestCase):
    """Icons from another toolkit are not in the catalog: they are downloaded and left as an inline image."""

    URL = f"{CDN}@v25.1.0/svg/vault.svg"
    SVG = b'<svg xmlns="http://www.w3.org/2000/svg"><path d="M0 0h1v1z"/></svg>'

    def embed_with_download(self, xml):
        with mock.patch.object(embed.urllib.request, "urlopen") as urlopen:
            urlopen.return_value.__enter__.return_value.read.return_value = self.SVG
            out, count = embed.embed(xml)
        return out, count, urlopen

    def test_a_url_from_another_toolkit_is_downloaded_and_inlined(self):
        style = f"shape=image;imageAspect=0;fontSize=9;ociIcon=vault;image={self.URL};"
        out, count, urlopen = self.embed_with_download(model(cell(style)))
        inline = "data:image/svg+xml," + base64.b64encode(self.SVG).decode()
        self.assertEqual(styles_of(out)[-1], f"shape=image;imageAspect=0;fontSize=9;ociIcon=vault;image={inline};")
        self.assertEqual(urlopen.call_args.args[0], self.URL)
        self.assertEqual(count, {"total": 1, "missing": []})

    def test_each_downloaded_icon_is_counted(self):
        other = self.URL.replace("vault", "waf")
        xml = model(cell(f"shape=image;image={self.URL};", "2"), cell(f"shape=image;ociIcon=waf;image={other};", "3"))
        out, count, urlopen = self.embed_with_download(xml)
        self.assertEqual(count["total"], 2)
        self.assertEqual(urlopen.call_count, 2)
        self.assertEqual(out.count("image=data:image/svg+xml,"), 2)


class LegacyStylesTest(unittest.TestCase):
    """A style written by each released tag becomes today's canonical stencil. Reads only the committed
    fixture, because CI checkouts carry no tags."""

    def test_every_released_form_becomes_the_current_canonical_stencil(self):
        slug = LEGACY["slug"]
        self.assertEqual([s["tag"] for s in LEGACY["styles"]], ["v24.2.1", "v24.2.2", "v24.2.3"])
        for entry in LEGACY["styles"]:
            with self.subTest(tag=entry["tag"], form=entry["form"]):
                with mock.patch.object(embed.urllib.request, "urlopen", side_effect=AssertionError("network access")):
                    out, count = embed.embed(model(cell(entry["estilo"])))
                self.assertEqual(styles_of(out)[-1], ICONS[slug]["style"])
                self.assertEqual(count, {"total": 1, "missing": []})

    def test_the_fixture_holds_the_three_forms_it_claims(self):
        forms = {e["tag"]: e["estilo"] for e in LEGACY["styles"]}
        self.assertIn(f"image={CDN}@v24.2.1/svg/", forms["v24.2.1"])
        self.assertNotIn("ociIcon", forms["v24.2.1"])
        self.assertIn("image=data:image/svg+xml,", forms["v24.2.2"])
        self.assertTrue(forms["v24.2.3"].startswith("shape=stencil("))


if __name__ == "__main__":
    unittest.main()
