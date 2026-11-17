"""Consistency between catalog.json, svg/, stencil.py, extract.py's templates and catalog.md."""
import re
import tempfile
import unittest
from pathlib import Path

from support import ROOT, load_catalog  # first: puts scripts/ on sys.path

import extract  # noqa: E402
import stencil  # noqa: E402

CATALOG = load_catalog()
STENCIL_PREFIX = re.compile(r"shape=stencil\(([^)]*)\);")


class CatalogShapeTest(unittest.TestCase):
    def test_top_level_keys_and_version(self):
        self.assertEqual(list(CATALOG), ["source", "version", "base_url", "icons", "containers"])
        self.assertEqual(CATALOG["version"], extract.VERSION)
        self.assertEqual(CATALOG["base_url"], extract.BASE_URL)
        self.assertEqual(CATALOG["source"], extract.SOURCE)
        self.assertNotIn("v24.2.", CATALOG["source"])  # the toolkit version, not this repo's revision

    def test_icon_keys_are_english_and_in_order(self):
        expected = ["slug", "label", "category", "width", "height", "file", "style", "url_style"]
        bad = [i["slug"] for i in CATALOG["icons"] if list(i) != expected]
        self.assertEqual(bad, [])

    def test_container_keys_are_english_and_in_order(self):
        for c in CATALOG["containers"]:
            self.assertEqual(list(c), ["type", "label", "style", "width", "height"])

    def test_slugs_are_unique_and_url_safe(self):
        slugs = [i["slug"] for i in CATALOG["icons"]]
        self.assertEqual(len(slugs), len(set(slugs)))
        self.assertTrue(all(re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", s) for s in slugs))

    def test_every_url_style_uses_the_current_version(self):
        marker = f"@{CATALOG['version']}/svg/"
        bad = [i["slug"] for i in CATALOG["icons"] if marker not in i["url_style"]]
        self.assertEqual(bad, [])

    def test_styles_follow_the_templates_of_extract(self):
        for i in CATALOG["icons"]:
            payload = STENCIL_PREFIX.match(i["style"]).group(1)
            self.assertEqual(i["style"], extract.STENCIL_STYLE.format(stencil=payload, slug=i["slug"]), i["slug"])
            url = f"{CATALOG['base_url']}/{i['slug']}.svg"
            self.assertEqual(i["url_style"], extract.URL_STYLE.format(slug=i["slug"], url=url), i["slug"])

    def test_the_ten_container_types_are_present(self):
        self.assertEqual([c["type"] for c in CATALOG["containers"]], list(extract.CONTAINERS))

    def test_every_icon_has_its_svg_and_no_svg_is_orphaned(self):
        listed = {Path(i["file"]).name for i in CATALOG["icons"]}
        on_disk = {p.name for p in (ROOT / "svg").glob("*.svg")}
        self.assertEqual(listed, on_disk)
        self.assertTrue(all(i["file"] == f"svg/{i['slug']}.svg" for i in CATALOG["icons"]))


class StencilConsistencyTest(unittest.TestCase):
    def test_stencil_of_each_svg_is_the_one_embedded_in_the_catalog(self):
        mismatches = []
        for i in CATALOG["icons"]:
            svg = (ROOT / i["file"]).read_text(encoding="utf-8")
            if stencil.stencil(svg) != STENCIL_PREFIX.match(i["style"]).group(1):
                mismatches.append(i["slug"])
        self.assertEqual(mismatches, [], "catalog.json is stale against svg/: re-run extract.py")


class MarkdownTest(unittest.TestCase):
    def test_catalog_md_is_what_write_markdown_produces_from_the_catalog(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "catalog.md"
            extract.write_markdown(CATALOG["icons"], CATALOG["containers"], target)
            generated = target.read_text(encoding="utf-8")
        self.assertEqual((ROOT / "catalog.md").read_text(encoding="utf-8"), generated)

    def test_catalog_md_lists_every_icon_once(self):
        text = (ROOT / "catalog.md").read_text(encoding="utf-8").split("## Containers")[0]
        for i in CATALOG["icons"]:
            self.assertEqual(text.count(f"| `{i['slug']}` |"), 1, i["slug"])


if __name__ == "__main__":
    unittest.main()
