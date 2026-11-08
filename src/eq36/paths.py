"""
Provide path resolution utilities.

These function centralize file resolution, e.g. finding the correct binary
executable to be run.
"""

import sys
from pathlib import Path


def get_bin() -> Path:
    """
    Get the path to the project `bin` directory.

    This directory contains the compiled binaries for EQ3/6.

    A `RuntimeError` is raised if the expected directory does not exist.
    """
    binpath = (Path(__file__).parent / "bin").resolve()
    if not binpath.is_dir():
        msg = f"{binpath} is not a directory"
        raise RuntimeError(msg)
    return binpath


def get_execpath(cmd: str | Path) -> Path:
    """
    Get the path to an executable in the project `bin` directory.

    This routine ensures that the `cmd` is appropriately suffixed with `'.exe'`
    on windows machines.

    A `RuntimeError` is raised if the file is not found.
    """
    suffix = ".exe" if sys.platform.startswith("win") and not str(cmd).endswith(".exe") else ""
    execpath = (get_bin() / (str(cmd) + suffix)).resolve()
    if not execpath.is_file():
        msg = f"{execpath!s} command not found"
        raise Exception(msg)
    return execpath


__all__ = [
    "get_bin",
    "get_execpath",
]
