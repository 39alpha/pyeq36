"""Test the path resolution utilities in `eq36.paths`."""

import sys
from pathlib import Path

import pytest

from eq36 import paths
from eq36.paths import get_bin, get_execpath, remove_exe


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
    with pytest.raises(RuntimeError, match="is not a directory") as excinfo:
        _ = get_bin()

    assert "EQ36_BIN" not in str(excinfo.value)


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


## The suffix of executables on the current platform
EXE_SUFFIX = ".exe" if sys.platform.startswith("win") else ""


def test_get_bin_uses_eq36_bin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `get_bin` returns the directory given by `EQ36_BIN`.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory to use as the `bin` directory
    """
    monkeypatch.setenv("EQ36_BIN", str(tmp_path))
    assert get_bin() == tmp_path.resolve()


def test_get_bin_ignores_empty_eq36_bin(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure that `get_bin` returns the bundled `bin` directory if `EQ36_BIN` is empty.

    @param monkeypatch The pytest monkeypatch fixture
    """
    monkeypatch.setenv("EQ36_BIN", "")
    assert get_bin() == (Path(paths.__file__).parent / "bin").resolve()


def test_get_bin_expands_user_in_eq36_bin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `~` in `EQ36_BIN` is expanded to the user's home directory.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory to use as the home directory
    """
    (tmp_path / "bin").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("USERPROFILE", str(tmp_path))
    monkeypatch.setenv("EQ36_BIN", str(Path("~", "bin")))
    assert get_bin() == (tmp_path / "bin").resolve()


def test_get_bin_resolves_relative_eq36_bin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that a relative `EQ36_BIN` is resolved against the current working directory.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory to use as the working directory
    """
    (tmp_path / "bin").mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("EQ36_BIN", "bin")
    assert get_bin() == (tmp_path / "bin").resolve()


@pytest.mark.parametrize("name", ["missing", "file"])
def test_get_bin_raises_if_eq36_bin_is_not_a_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
) -> None:
    """
    Ensure that `get_bin` raises a `RuntimeError`, naming `EQ36_BIN`, if `EQ36_BIN` is not a directory.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory in which `file` (but not `missing`) exists
    @param name        The name of the path, within `tmp_path`, to use as `EQ36_BIN`
    """
    (tmp_path / "file").touch()
    monkeypatch.setenv("EQ36_BIN", str(tmp_path / name))
    with pytest.raises(RuntimeError, match="from EQ36_BIN is not a directory"):
        _ = get_bin()


def test_get_execpath_uses_eq36_bin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `get_execpath` finds executables in the directory given by `EQ36_BIN`.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory to use as the `bin` directory
    """
    executable = tmp_path / f"eqpt{EXE_SUFFIX}"
    executable.touch()
    monkeypatch.setenv("EQ36_BIN", str(tmp_path))
    assert get_execpath("eqpt") == executable.resolve()


def test_get_execpath_raises_if_not_in_eq36_bin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `get_execpath` raises a `RuntimeError` if the executable is not in the directory given by `EQ36_BIN`.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    An empty temporary directory to use as the `bin` directory
    """
    monkeypatch.setenv("EQ36_BIN", str(tmp_path))
    with pytest.raises(RuntimeError, match="command not found"):
        _ = get_execpath("eqpt")


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        (Path("eqpt.exe"), Path("eqpt")),
        (Path("eqpt.EXE"), Path("eqpt")),
        (Path("bin", "eqpt.exe"), Path("bin", "eqpt")),
        (Path("eqpt"), Path("eqpt")),
        (Path("eqpt.txt"), Path("eqpt.txt")),
    ],
)
def test_remove_exe(path: Path, expected: Path) -> None:
    """
    Ensure that `remove_exe` removes an `.exe` suffix, ignoring case, and leaves other paths unchanged.

    @param path     The path from which to remove the suffix
    @param expected The expected path
    """
    assert remove_exe(path) == expected
