"""Every place that carries the release version agrees with `extract.VERSION`, the one the catalog is built from."""
import json
import re
import unittest

from support import ROOT, SKILL, load_catalog  # first: puts scripts/ on sys.path

import extract  # noqa: E402

VERSION = extract.VERSION            # "v24.2.4"
BARE = VERSION.removeprefix("v")     # "24.2.4": plugin manifests, SKILL.md and CHANGELOG headings


def read(path) -> str:
    return path.read_text(encoding="utf-8")


def read_json(path) -> dict:
    return json.loads(read(path))


class VersionAgreementTest(unittest.TestCase):
    def test_catalog_version_base_url_and_every_icon_url(self):
        catalog = load_catalog()
        self.assertEqual(catalog["version"], VERSION)
        self.assertEqual(catalog["base_url"], extract.BASE_URL)
        for icon in catalog["icons"]:
            self.assertTrue(icon["url_style"].endswith(f"@{VERSION}/svg/{icon['slug']}.svg"), icon["slug"])

    def test_the_skill_copy_of_the_catalog_has_the_same_version(self):
        self.assertEqual(read_json(SKILL / "catalog.json")["version"], VERSION)

    def test_catalog_md_header(self):
        self.assertIn(f"(release {VERSION})", read(ROOT / "catalog.md").splitlines()[2])

    def test_plugin_manifest(self):
        self.assertEqual(read_json(ROOT / ".claude-plugin" / "plugin.json")["version"], BARE)

    def test_marketplace_plugin_entry_and_metadata(self):
        marketplace = read_json(ROOT / ".claude-plugin" / "marketplace.json")
        entries = [p for p in marketplace["plugins"] if p["name"] == SKILL.name]
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0]["version"], BARE)
        if "metadata" in marketplace and "version" in marketplace["metadata"]:
            self.assertEqual(marketplace["metadata"]["version"], BARE)

    def test_skill_metadata_version(self):
        frontmatter = read(SKILL / "SKILL.md").split("---")[1]
        match = re.search(r'^\s+version:\s*"?([^"\s]+)"?\s*$', frontmatter, re.M)
        self.assertIsNotNone(match, "SKILL.md has no metadata.version")
        self.assertEqual(match.group(1), BARE)

    def test_every_cdn_url_in_the_readme(self):
        urls = re.findall(r"cth-oci-drawio-icons@(v[0-9][^/\s]*)/", read(ROOT / "README.md"))
        self.assertTrue(urls, "the README has no CDN URL")
        self.assertEqual(set(urls), {VERSION})

    def test_top_released_entry_of_the_changelog(self):
        headings = re.findall(r"^## (\S+)", read(ROOT / "CHANGELOG.md"), re.M)
        released = [h for h in headings if h != "Unreleased"]
        self.assertEqual(released[0], BARE)


if __name__ == "__main__":
    unittest.main()
