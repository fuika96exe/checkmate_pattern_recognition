"""Run the frozen gates against a copy of xq_classify with nothing from the lab importable.

Copies the package, both frozen sets and the two gate tests into a temporary directory, then runs the gates with
``python -I -S``: no site-packages, so no pyffish, FastAPI or Pydantic, and only a copy of pytest added to the path.
Two layouts:
  flat      the package imports as ``xq_classify``
  vendored  it imports as ``xiangqi_server.vendor.xq_classify``, the way xiangqi-server will use it, and the bare
            ``xq_classify`` name does not exist

The gates are copied unchanged, except that the vendored copy imports the vendored name. Their native runs need the
lab's pyffish adapter, so a stub reports it as unavailable and they skip through the gates' own branch. What remains
is every frozen case on the pure-Python board, with its colour-swapped and mirrored variants.

Usage (from the repository root):
  python backend/scripts/portability_check.py [--python <interpreter>] [--work-dir <directory>]
"""
from __future__ import annotations

import argparse
import importlib.util
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
GATES = ("test_midgame_frozen.py", "test_checkmate_frozen.py")
FROZEN_SETS = ("midgame_frozen", "checkmate_frozen")
PYTEST_AND_DEPENDENCIES = ("pytest", "_pytest", "py", "pluggy", "iniconfig", "packaging", "pygments", "colorama")
NEVER_IMPORTABLE = ("pyffish", "fastapi", "pydantic", "starlette", "uvicorn")
VENDORED_NAME = "xiangqi_server.vendor.xq_classify"
IGNORE_CACHES = shutil.ignore_patterns("__pycache__")
LAB_BOARD_STUB = "# The lab's pyffish adapter does not exist here, so the gates skip their native runs.\n" \
                 "pyffish = None\nNATIVE_BACKEND = None\n"

# Runs under ``python -I -S``: only the standard library until the copied pytest is on the path.
RUNNER = """
import importlib, importlib.util, pathlib, sys

root, dependencies, package, absent = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4].split(",")
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.path[:0] = [root, dependencies]
for name in absent:
    assert importlib.util.find_spec(name) is None, f"{name} must not be importable here"
module = importlib.import_module(package)
assert pathlib.Path(module.__file__).resolve().is_relative_to(pathlib.Path(root).resolve()), module.__file__
print("python", sys.version.split()[0], "package", module.__name__, module.__version__, flush=True)
import pytest
sys.exit(pytest.main(["tests", "-q", "-p", "no:cacheprovider", "--rootdir", root, "--basetemp", root + "/.tmp"]))
"""


def copy_pytest(target: Path) -> None:
    target.mkdir(parents=True)
    for name in PYTEST_AND_DEPENDENCIES:
        spec = importlib.util.find_spec(name)
        if spec is None or spec.origin is None:
            continue  # colorama is Windows-only
        origin = Path(spec.origin)
        if origin.name == "__init__.py":
            shutil.copytree(origin.parent, target / name, ignore=IGNORE_CACHES)
        else:
            shutil.copy2(origin, target)


def write_lab_stub(root: Path) -> None:
    """``app.board`` and ``backend.app.board``, the two names the gates import the adapter by."""
    for package in (root / "app", root / "backend" / "app"):
        package.mkdir(parents=True)
        (package / "__init__.py").write_text("", encoding="utf-8")
        (package / "board.py").write_text(LAB_BOARD_STUB, encoding="utf-8")
    (root / "backend" / "__init__.py").write_text("", encoding="utf-8")


def copy_gates(root: Path, package_name: str) -> None:
    tests = root / "tests"
    (tests / "fixtures").mkdir(parents=True)
    for name in FROZEN_SETS:
        shutil.copytree(BACKEND / "tests" / "fixtures" / name, tests / "fixtures" / name)
    for name in GATES:
        source = (BACKEND / "tests" / name).read_text(encoding="utf-8")
        text, imports = re.subn(r"^from xq_classify\b", f"from {package_name}", source, flags=re.MULTILINE)
        if not imports:
            raise SystemExit(f"{name} no longer imports xq_classify; update this script")
        (tests / name).write_text(text, encoding="utf-8", newline="\n")


def build(root: Path, vendored: bool) -> str:
    """Lay out one copy; return the name the package imports by."""
    if vendored:
        parent = root / "xiangqi_server" / "vendor"
        parent.mkdir(parents=True)
        for package in (root / "xiangqi_server", parent):
            (package / "__init__.py").write_text("", encoding="utf-8")
    else:
        parent = root
        root.mkdir(parents=True)
    shutil.copytree(BACKEND / "xq_classify", parent / "xq_classify", ignore=IGNORE_CACHES)
    package_name = VENDORED_NAME if vendored else "xq_classify"
    write_lab_stub(root)
    copy_gates(root, package_name)
    return package_name


def run(python: str, root: Path, dependencies: Path, package_name: str, vendored: bool) -> tuple[bool, str]:
    absent = [*NEVER_IMPORTABLE, *(("xq_classify",) if vendored else ())]
    completed = subprocess.run(
        [python, "-I", "-S", "-c", RUNNER, str(root), str(dependencies), package_name, ",".join(absent)],
        cwd=root, capture_output=True, encoding="utf-8", errors="replace", check=False,
    )
    output = completed.stdout + completed.stderr
    return completed.returncode == 0 and " passed" in output, output


def main() -> int:
    parser = argparse.ArgumentParser(description="Run the frozen gates against a stand-alone copy of xq_classify.")
    parser.add_argument("--python", default=sys.executable, help="interpreter to run the gates with")
    parser.add_argument("--work-dir", type=Path, help="where to create the temporary directory")
    args = parser.parse_args()
    passed = True
    with tempfile.TemporaryDirectory(prefix="xq-portability-", dir=args.work_dir) as temporary:
        base = Path(temporary)
        dependencies = base / "dependencies"
        copy_pytest(dependencies)
        for layout, vendored in (("flat", False), ("vendored", True)):
            root = base / layout
            package_name = build(root, vendored)
            succeeded, output = run(args.python, root, dependencies, package_name, vendored)
            passed = passed and succeeded
            lines = output.strip().splitlines()
            print(f"[{'PASS' if succeeded else 'FAIL'}] {layout}: {lines[0] if lines else ''} | {lines[-1] if lines else ''}")
            if not succeeded:
                print(output)
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
