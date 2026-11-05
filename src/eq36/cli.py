import sys
import os
from eq36.paths import get_execpath

def _run(cmd: str) -> None:
    """Execute a command, replacing the current process."""
    os.execv(get_execpath(cmd), sys.argv)

def eqpt() -> None:
    """Shim for running eqpt."""
    _run("eqpt")

def eq3nr() -> None:
    """Shim for running eq3nr"""
    _run("eq3nr")

def eq6() -> None:
    """Shim for running eq6"""
    _run("eq6")
