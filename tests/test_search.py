"""search.py: term search, --style with its budget line, --url, --containers and unknown slugs."""
import json
import math
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from support import ROOT, SKILL, load_catalog, run_main  # first: puts scripts/ on sys.path

import extract  # noqa: E402
import search  # noqa: E402

WARNING_FROM = math.ceil(search.BUDGET * search.BUDGET_WARNING_RATIO)  # first total that warns


def _icon(slug, label="Label", category="Category", style="s", url_style="u"):
    return dict(slug=slug, label=label, category=category, width=10, height=20, file=f"svg/{slug}.svg",
                style=style, url_style=url_style)


class SyntheticCatalogCase(unittest.TestCase):
    """Runs `search.main` against a small catalog written to a temp file."""

    def use_catalog(self, icons, containers=()):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        path = Path(tmp.name) / "catalog.json"
        path.write_text(json.dumps(dict(icons=list(icons), containers=list(containers))), encoding="utf-8")
        original = search.CATALOG
        search.CATALOG = path
        self.addCleanup(setattr, search, "CATALOG", original)


class TermSearchTest(SyntheticCatalogCase):
    def setUp(self):
        self.use_catalog([
            _icon("catalogo-nube", label="Catálogo de Nube", category="Gestión"),
            _icon("vault", label="Vault", category="Identity & Security"),
            _icon("key-vault", label="Key Vault", category="Identity & Security"),
        ])

    def test_accents_in_the_query_are_ignored(self):
        out, _, _ = run_main(search.main, ["CATÁLOGO"])
        self.assertEqual(out, "catalogo-nube | Catálogo de Nube | Gestión | 10x20\n")

    def test_accents_in_the_catalog_are_ignored(self):
        out, _, _ = run_main(search.main, ["gestion"])
        self.assertIn("catalogo-nube", out)

    def test_case_is_ignored(self):
        out, _, _ = run_main(search.main, ["KEY"])
        self.assertEqual(out.splitlines(), ["key-vault | Key Vault | Identity & Security | 10x20"])

    def test_every_term_must_match(self):
        out, _, _ = run_main(search.main, ["vault", "key"])
        self.assertEqual(out.splitlines(), ["key-vault | Key Vault | Identity & Security | 10x20"])

    def test_a_category_alone_matches(self):
        out, _, _ = run_main(search.main, ["identity"])
        self.assertEqual([l.split(" | ")[0] for l in out.splitlines()], ["vault", "key-vault"])

    def test_no_match_says_so_and_does_not_fail(self):
        out, _, code = run_main(search.main, ["zzz"])
        self.assertEqual(out, "no matches: try fewer words or another term\n")
        self.assertIsNone(code)

    def test_no_arguments_prints_usage_and_exits_non_zero(self):
        _, _, code = run_main(search.main, [])
        self.assertIn("Usage:", code)


class BudgetLineTest(SyntheticCatalogCase):
    """The budget line warns from 80 % of the budget (WARNING_FROM characters) up."""

    def style_line(self, total_chars):
        self.use_catalog([_icon("big", style="x" * total_chars)])
        out, _, _ = run_main(search.main, ["--style", "big"])
        return out.splitlines()[-1]

    def test_just_under_the_threshold_has_no_warning(self):
        line = self.style_line(WARNING_FROM - 1)
        self.assertIn(f"# {WARNING_FROM - 1} characters in styles", line)
        self.assertTrue(line.endswith(f"the full XML must stay under {search.BUDGET}"), line)

    def test_at_the_threshold_warns(self):
        line = self.style_line(WARNING_FROM)
        self.assertIn("it does not fit, use --url", line)

    def test_a_repeated_slug_counts_each_time(self):
        each = WARNING_FROM // 3 + 1  # one cell stays under the warning, three together pass it
        self.use_catalog([_icon("a", style="x" * each)])
        out, _, _ = run_main(search.main, ["--style", "a", "a", "a"])
        self.assertEqual(out.count("a | 10x20 |"), 3)
        self.assertIn(f"# {3 * each} characters", out)
        self.assertIn("it does not fit", out)

    def test_unknown_slug_is_reported_and_not_counted(self):
        self.use_catalog([_icon("a", style="x" * 7)])
        out, _, _ = run_main(search.main, ["--style", "ghost", "a"])
        self.assertIn("ghost | not in the catalog", out)
        self.assertIn("# 7 characters", out)

    def test_url_mode_has_no_budget_line(self):
        self.use_catalog([_icon("a", style="x" * 99_999, url_style="https://example.test/a.svg")])
        out, _, _ = run_main(search.main, ["--url", "a"])
        self.assertEqual(out, "a | 10x20 | https://example.test/a.svg\n")


class RealCatalogCliTest(unittest.TestCase):
    """The scripts as a user runs them, from the repository root and from the skill copy."""

    SCRIPTS_UNDER_TEST = [ROOT / "scripts" / "search.py", SKILL / "scripts" / "search.py"]

    def cli(self, script, *args):
        return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True)

    def test_style_of_known_icons_is_inline_stencil(self):
        for script in self.SCRIPTS_UNDER_TEST:
            with self.subTest(script=script):
                result = self.cli(script, "--style", "vault", "waf")
                self.assertEqual(result.returncode, 0, result.stderr)
                lines = result.stdout.splitlines()
                self.assertEqual(len(lines), 3)
                self.assertTrue(lines[0].startswith("vault | 42x40 | shape=stencil("))
                self.assertTrue(lines[1].startswith("waf | "))
                catalog = {i["slug"]: i for i in load_catalog()["icons"]}
                expected = len(catalog["vault"]["style"]) + len(catalog["waf"]["style"])
                self.assertTrue(lines[2].startswith(f"# {expected} characters in styles"), lines[2])

    def test_many_real_icons_exceed_the_budget_warning(self):
        size = len(next(i for i in load_catalog()["icons"] if i["slug"] == "vault")["style"])
        slugs = ["vault"] * (WARNING_FROM // size + 1)  # enough repeated cells to pass 80 % of the budget
        result = self.cli(self.SCRIPTS_UNDER_TEST[0], "--style", *slugs)
        self.assertIn("it does not fit, use --url", result.stdout.splitlines()[-1])

    def test_url_style_points_at_the_pinned_version(self):
        result = self.cli(self.SCRIPTS_UNDER_TEST[0], "--url", "vault")
        self.assertIn(f"image=https://cdn.jsdelivr.net/gh/CTH-SOLUCIONES/cth-oci-drawio-icons@{extract.VERSION}/svg/vault.svg",
                      result.stdout)

    def test_term_search_finds_kubernetes(self):
        for script in self.SCRIPTS_UNDER_TEST:
            with self.subTest(script=script):
                result = self.cli(script, "kubernetes")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("container-engine-for-kubernetes | OCI Container Engine for Kubernetes | "
                              "Developer Services | 42x42", result.stdout)

    def test_containers_lists_the_ten_types(self):
        result = self.cli(self.SCRIPTS_UNDER_TEST[1], "--containers")
        types = [line.split(" | ")[0] for line in result.stdout.splitlines()]
        self.assertEqual(types, ["region", "availability-domain", "fault-domain", "tenancy", "compartment",
                                 "vcn", "subnet", "oke-cluster", "on-premises", "internet"])

    def test_unknown_slug_for_the_real_catalog(self):
        result = self.cli(self.SCRIPTS_UNDER_TEST[0], "--style", "no-such-icon")
        self.assertIn("no-such-icon | not in the catalog", result.stdout)

    def test_no_arguments_exits_non_zero(self):
        result = self.cli(self.SCRIPTS_UNDER_TEST[0])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stderr)


if __name__ == "__main__":
    unittest.main()
