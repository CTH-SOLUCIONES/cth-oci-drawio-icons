"""SKILL.md only names icons and containers the catalog has, so the agent never copies a slug that does not exist."""
import re
import unittest

from support import SKILL, load_catalog  # first: puts scripts/ on sys.path

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


if __name__ == "__main__":
    unittest.main()
