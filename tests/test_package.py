"""package.py: --check for CI, sync direction, and the zip layout. Runs on a temp copy, never the real tree."""
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

from support import ROOT

SKILL_NAME = "oci-drawio-diagrams"
KEEP = ("catalog.json", "scripts", "skills")


class PackageCase(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / "repo"
        self.repo.mkdir()
        for name in KEEP:
            source = ROOT / name
            if source.is_dir():
                shutil.copytree(source, self.repo / name, ignore=shutil.ignore_patterns("__pycache__"))
            else:
                shutil.copy2(source, self.repo / name)
        self.skill = self.repo / "skills" / SKILL_NAME

    def package(self, *args):
        return subprocess.run([sys.executable, str(self.repo / "scripts" / "package.py"), *args],
                              capture_output=True, text=True)


class CheckTest(PackageCase):
    def test_the_committed_tree_is_in_sync(self):
        result = self.package("--check")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_check_writes_nothing(self):
        self.package("--check")
        self.assertFalse((self.repo / "dist").exists())

    def test_a_modified_skill_copy_fails_and_is_named(self):
        with open(self.skill / "catalog.json", "a", encoding="utf-8") as f:
            f.write(" ")  # one byte
        result = self.package("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skills/oci-drawio-diagrams/catalog.json", result.stderr)
        self.assertFalse((self.repo / "dist").exists())

    def test_check_does_not_repair_what_it_reports(self):
        target = self.skill / "scripts" / "search.py"
        target.write_text(target.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
        self.package("--check")
        self.assertIn("# tampered", target.read_text(encoding="utf-8"))

    def test_a_changed_root_source_not_yet_synced_fails(self):
        embed = self.repo / "scripts" / "embed.py"
        embed.write_text(embed.read_text(encoding="utf-8") + "\n# edited at the root\n", encoding="utf-8")
        result = self.package("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("scripts/embed.py", result.stderr)

    def test_a_missing_file_in_the_skill_fails(self):
        (self.skill / "scripts" / "embed.py").unlink()
        result = self.package("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("missing in the skill: scripts/embed.py", result.stderr)

    def test_leftovers_of_earlier_formats_fail(self):
        (self.skill / "svg").mkdir()
        result = self.package("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("svg", result.stderr)

    def test_extra_files_in_the_skill_fail_and_are_named(self):
        (self.skill / "notes.txt").write_text("x")
        (self.skill / "scripts").joinpath("helper.py").write_text("x")
        result = self.package("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("skills/oci-drawio-diagrams/notes.txt", result.stderr)
        self.assertIn("skills/oci-drawio-diagrams/scripts/helper.py", result.stderr)

    def test_pycache_and_ds_store_are_not_extra_files(self):
        (self.skill / "scripts" / "__pycache__").mkdir()
        (self.skill / "scripts" / "__pycache__" / "x.pyc").write_bytes(b"x")
        (self.skill / ".DS_Store").write_bytes(b"x")
        self.assertEqual(self.package("--check").returncode, 0)

    def test_a_leftover_file_is_reported_once_not_also_as_an_extra(self):
        (self.skill / "svg").mkdir()
        (self.skill / "svg" / "vault.svg").write_text("x")
        result = self.package("--check")
        self.assertEqual(result.stderr.count("svg"), 1, result.stderr)

    def test_unknown_arguments_are_rejected(self):
        result = self.package("--chek")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Usage:", result.stderr)

    def test_every_problem_is_listed_not_just_the_first(self):
        (self.skill / "catalog.json").write_text("{}", encoding="utf-8")
        (self.skill / "scripts" / "embed.py").unlink()
        result = self.package("--check")
        self.assertIn("catalog.json", result.stderr)
        self.assertIn("embed.py", result.stderr)


class SyncTest(PackageCase):
    def test_sync_repairs_a_tampered_copy_and_check_then_passes(self):
        (self.skill / "catalog.json").write_text("{}", encoding="utf-8")
        self.assertNotEqual(self.package("--check").returncode, 0)
        result = self.package()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.package("--check").returncode, 0)
        self.assertEqual((self.skill / "catalog.json").read_bytes(), (self.repo / "catalog.json").read_bytes())

    def test_sync_deletes_the_real_legacy_file_and_folder(self):
        (self.skill / "iconos.json").write_text("{}")
        (self.skill / "svg").mkdir()
        (self.skill / "svg" / "vault.svg").write_text("x")
        self.assertEqual(self.package().returncode, 0)
        self.assertFalse((self.skill / "iconos.json").exists())
        self.assertFalse((self.skill / "svg").exists())
        self.assertEqual(self.package("--check").returncode, 0)

    def test_sync_goes_from_the_root_to_the_skill_and_never_back(self):
        root_search = self.repo / "scripts" / "search.py"
        root_search.write_text(root_search.read_text(encoding="utf-8") + "\n# new at the root\n", encoding="utf-8")
        (self.skill / "scripts" / "embed.py").write_text("# stale copy\n", encoding="utf-8")
        self.package()
        self.assertIn("# new at the root", (self.skill / "scripts" / "search.py").read_text(encoding="utf-8"))
        self.assertNotIn("stale", (self.repo / "scripts" / "embed.py").read_text(encoding="utf-8"))

    def test_zip_has_the_skill_folder_as_root_and_only_four_files(self):
        self.package()
        with zipfile.ZipFile(self.repo / "dist" / f"{SKILL_NAME}.zip") as z:
            names = sorted(z.namelist())
        self.assertEqual(names, [f"{SKILL_NAME}/SKILL.md", f"{SKILL_NAME}/catalog.json",
                                 f"{SKILL_NAME}/scripts/embed.py", f"{SKILL_NAME}/scripts/search.py"])

    def test_zip_leaves_out_pycache_and_ds_store(self):
        (self.skill / "scripts" / "__pycache__").mkdir()
        (self.skill / "scripts" / "__pycache__" / "x.pyc").write_bytes(b"x")
        (self.skill / ".DS_Store").write_bytes(b"x")
        self.package()
        with zipfile.ZipFile(self.repo / "dist" / f"{SKILL_NAME}.zip") as z:
            self.assertEqual(len(z.namelist()), 4)

    def test_more_than_200_files_is_refused(self):
        for n in range(200):
            (self.skill / f"extra{n}.txt").write_text("x")
        result = self.package()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("200", result.stderr)


if __name__ == "__main__":
    unittest.main()
