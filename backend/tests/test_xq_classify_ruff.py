"""The portable package must stay clean under xiangqi-server's ruff settings (backend/ruff.toml)."""
import subprocess
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]


@pytest.mark.parametrize(
    "command",
    [["check", "--no-cache", "xq_classify"], ["format", "--no-cache", "--check", "xq_classify"]],
    ids=["lint", "format"],
)
def test_package_passes_ruff(command):
    result = subprocess.run([sys.executable, "-m", "ruff", *command], cwd=BACKEND, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
