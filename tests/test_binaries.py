"""Ensure that the compiles EQ36 binaries are installed."""

import os
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("executable", ["eqpt", "eq3nr", "eq6"])
def test_binaries_are_installed(executable: str) -> None:
    """Ensure that the binaries are installed."""
    if sys.platform == "win32":
        executable += ".exe"

    found = [exe for p in os.get_exec_path() if (exe := Path(p) / executable).exists()]
    assert len(found) != 0

    local = [exe for exe in found if str(exe).endswith(f".venv/bin/{executable}")]
    assert len(local) != 0
