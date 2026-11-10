"""
Ensure that the EQ3/6 shim scripts are installed and executable.

**Linux and MacOS Only**: It is tricky to find installed executables on Windows,
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
def test_shims_are_installed_and_executable(executable: str) -> None:
    """
    Ensure that the shims are installed and executable.

    We do this by explicitly searching the path for `.venv/bin/{executable}`
    and executing it without arguments, expecting nothing on `stdout` and a
    usage message on `stderr`.

    @param executable The name of the EQ3/6 shim to search for
    """
    found = [exe for p in os.get_exec_path() if (exe := Path(p) / executable).exists()]
    assert len(found) != 0

    local = [exe for exe in found if str(exe).endswith(f".venv/bin/{executable}")]
    assert len(local) != 0

    cmd = local[0]
    process = Popen([cmd], stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate(timeout=100)
    assert len(stdout) == 0
    assert stderr.startswith(b" usage:")
