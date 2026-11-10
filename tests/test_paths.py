"""Test the path resolution utilities in `eq36.paths`."""

import sys
from pathlib import Path

import pytest

from eq36 import paths
from eq36.paths import get_bin, get_execpath


def test_get_bin() -> None:
    """Ensure that `get_bin` returns the package `bin` directory."""
    assert str(get_bin()).endswith(str(Path("eq36", "bin")))


@pytest.mark.parametrize("executable", ["eqpt", "eq3nr", "eq6"])
def test_executable_paths_are_found(executable: str) -> None:
    """
    Ensure that executables are found.

    On Windows, the path is expected to have an `.exe` suffix.

    @param executable The name of the EQ3/6 executable to find
    """
    expected = executable if not sys.platform.startswith("win") else (executable + ".exe")
    assert str(get_execpath(executable)).endswith(str(Path("eq36", "bin", expected)))


def test_get_bin_raises_if_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `get_bin` raises a `RuntimeError` if the `bin` directory does not exist.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory without a `bin` subdirectory
    """
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "paths.py"))
    with pytest.raises(RuntimeError, match="is not a directory"):
        _ = get_bin()


def test_get_execpath_raises_if_bin_is_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `get_execpath` raises a `RuntimeError` if the `bin` directory does not exist.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory without a `bin` subdirectory
    """
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "paths.py"))
    with pytest.raises(RuntimeError, match="is not a directory"):
        _ = get_execpath("eqpt")


def test_get_execpath_raises_if_not_found() -> None:
    """Ensure that `get_execpath` raises a `RuntimeError` if the executable does not exist."""
    with pytest.raises(RuntimeError, match="command not found"):
        _ = get_execpath("not-an-eq36-executable")


@pytest.mark.skipif(sys.platform.startswith("win"), reason="the executables are suffixed on windows")
@pytest.mark.parametrize("executable", ["eqpt", "eqpt.exe"])
def test_get_execpath_adds_exe_suffix_on_windows(monkeypatch: pytest.MonkeyPatch, executable: str) -> None:
    """
    Ensure that `get_execpath` searches for an `.exe` suffixed executable on Windows.

    The platform is faked, so the unsuffixed executable that is installed is
    not found; the error message reveals which file was searched for. A
    command which is already suffixed should not be suffixed again.

    @param monkeypatch The pytest monkeypatch fixture
    @param executable  The name of the command to search for
    """
    monkeypatch.setattr(sys, "platform", "win32")
    with pytest.raises(RuntimeError, match=r"[/\\]eqpt\.exe command not found"):
        _ = get_execpath(executable)
