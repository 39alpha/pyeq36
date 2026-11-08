"""
Ensure that the compiles EQ36 binaries are installed.

**Linux and MacOS Only**: It is tricky to find installed excutables on Windows,
so we skip this test.
"""

import os
import sys
from pathlib import Path

import pytest

if sys.platform.startswith("win"):
    pytest.skip("skipping unix-only tests", allow_module_level=True)


@pytest.mark.parametrize("executable", ["eqpt", "eq3nr", "eq6"])
def test_binaries_are_installed(executable: str) -> None:
    """
    Ensure that the binaries are installed.

    We do this by explicitly searching the path for .venv/bin/{executable}.
    """
    found = [exe for p in os.get_exec_path() if (exe := Path(p) / executable).exists()]
    assert len(found) != 0

    local = [exe for exe in found if str(exe).endswith(f".venv/bin/{executable}")]
    assert len(local) != 0
