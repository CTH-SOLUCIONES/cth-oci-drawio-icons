"""Shared helpers for the tests: repository paths and an importable `scripts/` folder."""
import contextlib
import io
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS = ROOT / "scripts"
SKILL = ROOT / "skills" / "oci-drawio-diagrams"

if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))


def load_catalog() -> dict:
    return json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))


def run_main(main, args: list[str]) -> tuple[str, str, int | str | None]:
    """Run a script's `main(args)` in process; return (stdout, stderr, exit code).

    The exit code is None when `main` returns normally and the `SystemExit` argument otherwise.
    """
    out, err = io.StringIO(), io.StringIO()
    code = None
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        try:
            main(args)
        except SystemExit as exit_:
            code = exit_.code
    return out.getvalue(), err.getvalue(), code
