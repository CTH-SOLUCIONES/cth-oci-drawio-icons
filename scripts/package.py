#!/usr/bin/env python3
"""Make the skill self-contained and build the .zip to upload it to the organization in Claude.

The skill carries its own copy of the catalog, which holds every icon as an inline stencil, and of
the scripts: in claude.ai the execution environment only reaches package managers by default, so it
cannot depend on the CDN to embed. Everything fits in four files; claude.ai rejects zips of more
than 200. The source of truth stays the repository root; this script copies into the skill, never
the other way around.

Usage:
  package.py           # sync skills/oci-drawio-diagrams/ and write dist/oci-drawio-diagrams.zip
  package.py --check   # write nothing; exit non-zero listing what differs (for CI)
"""
import shutil
import sys
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL = ROOT / "skills" / "oci-drawio-diagrams"
# root source -> path inside the skill
COPIES = {"catalog.json": "catalog.json",
          "scripts/embed.py": "scripts/embed.py", "scripts/search.py": "scripts/search.py"}
# Earlier formats: one SVG per file, then all the SVGs in iconos.json. Sync removes them.
LEGACY_PATHS = ("svg", "iconos.json")
IGNORED = {".DS_Store", "__pycache__"}
MAX_FILES = 200  # what the skill upload in claude.ai accepts


def sync() -> None:
    for source, target in COPIES.items():
        (SKILL / target).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / source, SKILL / target)
    for legacy in LEGACY_PATHS:
        shutil.rmtree(SKILL / legacy, ignore_errors=True)
        (SKILL / legacy).unlink(missing_ok=True)


def differences() -> list[str]:
    """What keeps the skill copy from being byte-identical to the root sources; empty if in sync."""
    problems = []
    for source, target in COPIES.items():
        copy = SKILL / target
        if not copy.is_file():
            problems.append(f"missing in the skill: {target}")
        elif copy.read_bytes() != (ROOT / source).read_bytes():
            problems.append(f"differs from {source}: {copy.relative_to(ROOT)}")
    problems += [f"leftover from an earlier format: {(SKILL / p).relative_to(ROOT)}"
                 for p in LEGACY_PATHS if (SKILL / p).exists()]
    expected = {"SKILL.md", *COPIES.values()}
    legacy = [SKILL / p for p in LEGACY_PATHS]
    problems += [f"extra file in the skill, delete it: {f.relative_to(ROOT)}"
                 for f in sorted(SKILL.rglob("*"))
                 if f.is_file() and not IGNORED.intersection(f.parts)
                 and f.relative_to(SKILL).as_posix() not in expected
                 and not any(f == p or p in f.parents for p in legacy)]
    return problems


def build_zip() -> Path:
    # claude.ai requires the skill folder as the zip root, with the skill's own name.
    files = [f for f in sorted(SKILL.rglob("*")) if f.is_file() and not IGNORED.intersection(f.parts)]
    if len(files) > MAX_FILES:
        raise SystemExit(f"the skill has {len(files)} files; claude.ai accepts up to {MAX_FILES}")
    output = ROOT / "dist" / f"{SKILL.name}.zip"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as z:
        for f in files:
            z.write(f, Path(SKILL.name) / f.relative_to(SKILL))
    return output


def main(args: list[str]) -> None:
    if args == ["--check"]:
        problems = differences()
        if problems:
            sys.exit("the skill copy is out of sync with the repository root; run scripts/package.py:\n  "
                     + "\n  ".join(problems))
        print("the skill copy is identical to the root sources")
    elif args:
        sys.exit(__doc__)
    else:
        sync()
        archive = build_zip()
        with zipfile.ZipFile(archive) as z:
            count = len(z.namelist())
        print(f"skill synced; {archive.relative_to(ROOT)}: {count} files, {archive.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main(sys.argv[1:])
