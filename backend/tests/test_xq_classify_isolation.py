"""xq_classify must stay portable.

Phase 1 vendors the package into xiangqi-server as
``xiangqi_server.vendor.xq_classify`` and runs it in background workers. The lab
also runs it on Cloudflare, where threads are not available. So inside the package:

* only standard-library imports, plus relative imports between its own modules;
* no absolute ``xq_classify`` import (it would break under a vendor parent);
* no threads or processes, and no file, network or dynamic-import machinery;
* syntax that Python 3.12 accepts (3.13 accepts a superset).

The static scan catches what is written. The two import tests prove that the
package actually loads in a clean interpreter: once as ``xq_classify`` with the
lab and its third-party dependencies blocked, once under a vendor parent with the
bare ``xq_classify`` name blocked as well.
"""
import ast
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
PACKAGE = BACKEND / "xq_classify"
SOURCES = sorted(PACKAGE.rglob("*.py"))

FORBIDDEN_MODULES = {
    # threads and processes: Cloudflare has none, background workers own their own
    "threading", "_thread", "multiprocessing", "concurrent", "asyncio", "subprocess",
    # I/O and environment: the package is pure computation
    "os", "io", "pathlib", "shutil", "tempfile", "socket", "ssl", "urllib", "http",
    # dynamic imports would hide dependencies from this scan
    "importlib",
}
FORBIDDEN_CALLS = {"open", "print", "input", "breakpoint", "exec", "eval", "__import__"}
# Never importable while the package loads: the lab and its runtime dependencies.
LAB_AND_THIRD_PARTY = ["app", "backend", "scripts", "pyffish", "fastapi", "pydantic", "starlette"]


def _violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=(3, 12))
    found = []
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.level > 0:
            continue  # relative import between the package's own modules
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = [alias.name for alias in node.names] if isinstance(node, ast.Import) else [node.module]
            for name in names:
                top = name.split(".")[0]
                if top == "xq_classify":
                    found.append(f"{node.lineno}: absolute import of {name}; use a relative import")
                elif top not in sys.stdlib_module_names:
                    found.append(f"{node.lineno}: {name} is not in the standard library")
                elif top in FORBIDDEN_MODULES:
                    found.append(f"{node.lineno}: {name} is forbidden in the package")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            found.append(f"{node.lineno}: call to {node.func.id}()")
    return found


def test_package_sources_exist():
    assert (PACKAGE / "__init__.py").is_file()
    assert len(SOURCES) >= 5, SOURCES


@pytest.mark.parametrize("path", SOURCES, ids=[p.relative_to(PACKAGE).as_posix() for p in SOURCES])
def test_source_is_isolated(path):
    found = _violations(path)
    assert not found, f"{path.relative_to(BACKEND).as_posix()}:\n  " + "\n  ".join(found)


IMPORT_PROBE = """
import importlib, json, pkgutil, sys

root, package, blocked = sys.argv[1], sys.argv[2], set(json.loads(sys.argv[3]))

class Block:
    def find_spec(self, name, path=None, target=None):
        if name.split(".")[0] in blocked:
            raise ImportError(f"blocked import: {name}")
        return None

sys.meta_path.insert(0, Block())
sys.path.insert(0, root)
module = importlib.import_module(package)
names = [module.__name__]
for info in pkgutil.walk_packages(module.__path__, package + "."):
    importlib.import_module(info.name)
    names.append(info.name)
print(json.dumps({"modules": names, "version": module.__version__}))
"""


def _import_everything(root: Path, package: str, blocked: list[str]) -> dict:
    """Import the package and every submodule in a fresh ``python -I`` (no site, no PYTHONPATH, no cwd)."""
    completed = subprocess.run(
        [sys.executable, "-I", "-c", IMPORT_PROBE, str(root), package, json.dumps(blocked)],
        capture_output=True, text=True, timeout=120, check=False,
    )
    assert completed.returncode == 0, completed.stderr
    return json.loads(completed.stdout)


def test_package_imports_without_lab_or_third_party():
    import xq_classify

    loaded = _import_everything(BACKEND, "xq_classify", LAB_AND_THIRD_PARTY)
    assert loaded["version"] == xq_classify.__version__
    assert len(loaded["modules"]) == len(SOURCES), loaded["modules"]


def test_package_imports_when_vendored(tmp_path):
    """The layout xiangqi-server uses; the bare ``xq_classify`` name is blocked, so any absolute import fails."""
    vendor = tmp_path / "xiangqi_server" / "vendor"
    shutil.copytree(PACKAGE, vendor / "xq_classify", ignore=shutil.ignore_patterns("__pycache__"))
    for parent in (tmp_path / "xiangqi_server", vendor):
        (parent / "__init__.py").write_text("", encoding="utf-8")

    loaded = _import_everything(tmp_path, "xiangqi_server.vendor.xq_classify", [*LAB_AND_THIRD_PARTY, "xq_classify"])
    assert len(loaded["modules"]) == len(SOURCES), loaded["modules"]
