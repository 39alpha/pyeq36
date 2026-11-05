from typing import Never
import sys
import os
from eq36.paths import get_execpath

def _run(cmd: str) -> Never:
    """Execute a command, replacing the current process."""
    os.execv(get_execpath(cmd), sys.argv)

def eqpt() -> Never:
    """Shim for running eqpt."""
    _run("eqpt")

def eq3nr() -> Never:
    """Shim for running eq3nr"""
    _run("eq3nr")

def eq6() -> Never:
    """Shim for running eq6"""
    _run("eq6")
