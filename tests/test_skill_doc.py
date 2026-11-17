"""SKILL.md only names icons and containers the catalog has, and states the same XML budget as search.py."""
import re
import unittest

from support import ROOT, SKILL, load_catalog  # first: puts scripts/ on sys.path

import search  # noqa: E402

BODY = (SKILL / "SKILL.md").read_text(encoding="utf-8")
SLUG = re.compile(r"`([a-z0-9]+(?:-[a-z0-9]+)*)`")


def quick_reference_slugs() -> set[str]:
    """Every backticked slug in the rows of SKILL.md's table of most-used services."""
    rows = [line for line in BODY.splitlines() if line.startswith("|") and "`" in line]
    return {slug for row in rows for slug in SLUG.findall(row)}


def named_container_types() -> set[str]:
    """The backticked types in the paragraph that starts `There are ten containers`."""
    paragraph = re.search(r"^There are .*? containers:.*?(?:\n\n|\Z)", BODY, re.S | re.M)
    return set(SLUG.findall(paragraph.group(0))) if paragraph else set()


class SkillReferencesTest(unittest.TestCase):
    def test_every_quick_reference_slug_is_in_the_catalog(self):
        slugs = quick_reference_slugs()
        self.assertGreaterEqual(len(slugs), 30, "the table was not parsed")
        self.assertEqual(sorted(slugs - {i["slug"] for i in load_catalog()["icons"]}), [])

    def test_every_named_container_type_is_in_the_catalog(self):
        named = named_container_types()
        self.assertGreaterEqual(len(named), 10, "the container sentence was not parsed")
        self.assertEqual(sorted(named - {c["type"] for c in load_catalog()["containers"]}), [])


class BudgetFigureTest(unittest.TestCase):
    """The XML budget the agent reads in SKILL.md, and the one the README explains, is the one search.py enforces."""

    FIGURE = re.compile(r"under ([\d,]+) characters|([\d,]+)-character budget")

    def test_docs_state_only_the_scripts_budget(self):
        expected = {f"{search.BUDGET:,}"}
        for path in (SKILL / "SKILL.md", ROOT / "README.md", ROOT / "CONTRIBUTING.md"):
            with self.subTest(file=path.name):
                text = path.read_text(encoding="utf-8")
                found = {a or b for a, b in self.FIGURE.findall(text)}
                self.assertTrue(found, "no budget figure found")
                self.assertEqual(found, expected)


if __name__ == "__main__":
    unittest.main()
