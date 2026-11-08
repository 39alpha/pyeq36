"""
Ensure that the EQ3/6 shim scripts are installed and executable.

**Linux and MacOS Only**: It is tricky to find installed excutables on Windows,
so we skip this test.
"""

import os
import sys
from pathlib import Path
from subprocess import PIPE, Popen

import pytest

if sys.platform.startswith("win"):
    pytest.skip("skipping unix-only tests", allow_module_level=True)


@pytest.mark.parametrize("executable", ["eqpt", "eq3nr", "eq6"])
def test_shims_are_installed(executable: str) -> None:
    """
    Ensure that the shims are installed.

    We do this by explicitly searching the path for .venv/bin/{executable}.
    """
    found = [exe for p in os.get_exec_path() if (exe := Path(p) / executable).exists()]
    assert len(found) != 0

    local = [exe for exe in found if str(exe).endswith(f".venv/bin/{executable}")]
    assert len(local) != 0


@pytest.mark.parametrize("executable", ["eqpt", "eq3nr", "eq6"])
def test_shims_are_executable(executable: str) -> None:
    """
    Ensure that the shims are executable.

    We do this by finding the executable and ensuring that we can execute it.
    """
    found = [exe for p in os.get_exec_path() if (exe := Path(p) / executable).exists()]
    local = [exe for exe in found if str(exe).endswith(f".venv/bin/{executable}")]
    cmd = local[0]
    process = Popen([cmd], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate(timeout=100)
    assert len(stdout) == 0
    assert stderr.startswith(b" usage:")
