"""Tests paths."""

import sys
from pathlib import Path

import pytest

from eq36.paths import get_bin, get_execpath


def test_get_bin() -> None:
    """Ensure that get_bin returns the bin directory."""
    assert str(get_bin()).endswith(str(Path("eq36", "bin")))


@pytest.mark.parametrize("executable", ["eqpt", "eq3nr", "eq6"])
def test_executable_paths_are_found(executable: str) -> None:
    """Ensure that executables are found."""
    expected = executable if not sys.platform.startswith("win") else (executable + ".exe")
    assert str(get_execpath(executable)).endswith(str(Path("eq36", "bin", expected)))
