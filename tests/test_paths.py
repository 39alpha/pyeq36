"""Test the path resolution utilities in `eq36.paths`."""

import errno
import sys
from pathlib import Path

import pytest

from eq36 import paths
from eq36.paths import check_encodable, get_bin, get_execpath, get_lib, get_libpath, remove_exe

from .ansi import ANSI_UNENCODABLE, NON_ASCII, ansi_encodable, requires_non_ascii


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
    Ensure that `get_bin` raises a `FileNotFoundError`, naming the path, if the `bin` directory does not exist.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory without a `bin` subdirectory
    """
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "paths.py"))
    with pytest.raises(FileNotFoundError, match="does not exist") as excinfo:
        _ = get_bin()

    assert excinfo.value.errno == errno.ENOENT
    assert excinfo.value.filename == str((tmp_path / "bin").resolve())
    assert str(excinfo.value).count(repr(excinfo.value.filename)) == 1
    assert "EQ36_BIN" not in str(excinfo.value)


def test_get_bin_raises_if_not_a_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `get_bin` raises a `NotADirectoryError`, naming the path, if the `bin` path is a file.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory in which `bin` is a file
    """
    (tmp_path / "bin").touch()
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "paths.py"))
    with pytest.raises(NotADirectoryError, match="is not a directory") as excinfo:
        _ = get_bin()

    assert str((tmp_path / "bin").resolve()) in str(excinfo.value)
    assert "EQ36_BIN" not in str(excinfo.value)


def test_get_execpath_raises_if_bin_is_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `get_execpath` raises a `FileNotFoundError` if the `bin` directory does not exist.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory without a `bin` subdirectory
    """
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "paths.py"))
    with pytest.raises(FileNotFoundError, match="does not exist"):
        _ = get_execpath("eqpt")


def test_get_execpath_raises_if_not_found() -> None:
    """Ensure that `get_execpath` raises a `FileNotFoundError`, naming the path, if the executable does not exist."""
    with pytest.raises(FileNotFoundError, match="command not found") as excinfo:
        _ = get_execpath("not-an-eq36-executable")

    assert excinfo.value.errno == errno.ENOENT
    assert Path(excinfo.value.filename).name.startswith("not-an-eq36-executable")
    assert str(excinfo.value).count(repr(excinfo.value.filename)) == 1


@pytest.mark.skipif(sys.platform.startswith("win"), reason="the executables are suffixed on windows")
@pytest.mark.parametrize("executable", ["eqpt", "eqpt.exe"])
def test_get_execpath_adds_exe_suffix_on_windows(monkeypatch: pytest.MonkeyPatch, executable: str) -> None:
    """
    Ensure that `get_execpath` searches for an `.exe` suffixed executable on Windows.

    The platform is faked, so the unsuffixed executable that is installed is
    not found; the error's `filename` reveals which file was searched for. A
    command which is already suffixed should not be suffixed again.

    @param monkeypatch The pytest monkeypatch fixture
    @param executable  The name of the command to search for
    """
    monkeypatch.setattr(sys, "platform", "win32")
    with pytest.raises(FileNotFoundError, match="command not found") as excinfo:
        _ = get_execpath(executable)

    assert Path(excinfo.value.filename).name == "eqpt.exe"


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


@pytest.mark.parametrize(
    ("name", "error", "match"),
    [
        ("missing", FileNotFoundError, "from EQ36_BIN does not exist"),
        ("file", NotADirectoryError, "from EQ36_BIN is not a directory"),
    ],
)
def test_get_bin_raises_if_eq36_bin_is_not_a_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    name: str,
    error: type[OSError],
    match: str,
) -> None:
    """
    Ensure that `get_bin` raises an appropriate `OSError`, naming `EQ36_BIN`, if `EQ36_BIN` is not a directory.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory in which `file` (but not `missing`) exists
    @param name        The name of the path, within `tmp_path`, to use as `EQ36_BIN`
    @param error       The type of error expected
    @param match       A pattern the error message is expected to match
    """
    (tmp_path / "file").touch()
    monkeypatch.setenv("EQ36_BIN", str(tmp_path / name))
    with pytest.raises(error, match=match):
        _ = get_bin()


@pytest.mark.skipif(sys.platform.startswith("win"), reason="`~user` does not fail to expand on Windows")
def test_get_bin_raises_if_eq36_bin_cannot_be_expanded(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure that `get_bin` raises a `FileNotFoundError`, naming `EQ36_BIN`, if `EQ36_BIN` cannot be expanded.

    `Path.expanduser` raises a `RuntimeError` for `~user` if the user is
    unknown; this is the cause of the raised error.

    @param monkeypatch The pytest monkeypatch fixture
    """
    path = "~not-an-eq36-user/bin"
    monkeypatch.setenv("EQ36_BIN", path)
    with pytest.raises(FileNotFoundError, match="from EQ36_BIN does not exist") as excinfo:
        _ = get_bin()

    assert excinfo.value.errno == errno.ENOENT
    assert excinfo.value.filename == path
    assert isinstance(excinfo.value.__cause__, RuntimeError)


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


def test_get_execpath_searches_subdirectories(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `get_execpath` searches the subdirectory of `bin` given by the parent of the command.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory to use as the `bin` directory
    """
    (tmp_path / "tools").mkdir()
    executable = tmp_path / "tools" / f"eqpt{EXE_SUFFIX}"
    executable.touch()
    monkeypatch.setenv("EQ36_BIN", str(tmp_path))
    assert get_execpath(Path("tools", "eqpt")) == executable.resolve()


def test_get_execpath_ignores_case_of_exe_suffix(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that, on Windows, `get_execpath` does not add `.exe` to a command already suffixed in another case.

    The platform is faked, so the command must be found as given rather than
    with a second suffix, i.e. `eqpt.EXE.exe`.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory to use as the `bin` directory
    """
    executable = tmp_path / "eqpt.EXE"
    executable.touch()
    monkeypatch.setenv("EQ36_BIN", str(tmp_path))
    monkeypatch.setattr(sys, "platform", "win32")
    assert get_execpath("eqpt.EXE") == executable.resolve()


def test_get_execpath_raises_if_not_in_eq36_bin(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `get_execpath` raises a `FileNotFoundError` if the executable is not in the `EQ36_BIN` directory.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    An empty temporary directory to use as the `bin` directory
    """
    monkeypatch.setenv("EQ36_BIN", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="command not found"):
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


def test_get_lib() -> None:
    """Ensure that `get_lib` returns the package `lib` directory."""
    assert get_lib() == (Path(paths.__file__).parent / "lib").resolve()


def test_get_lib_raises_if_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `get_lib` raises a `FileNotFoundError`, naming the path, if the `lib` directory does not exist.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory without a `lib` subdirectory
    """
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "paths.py"))
    with pytest.raises(FileNotFoundError, match="does not exist") as excinfo:
        _ = get_lib()

    assert excinfo.value.errno == errno.ENOENT
    assert excinfo.value.filename == str((tmp_path / "lib").resolve())
    assert str(excinfo.value).count(repr(excinfo.value.filename)) == 1


def test_get_lib_raises_if_not_a_directory(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `get_lib` raises a `NotADirectoryError`, naming the path, if the `lib` path is a file.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory in which `lib` is a file
    """
    (tmp_path / "lib").touch()
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "paths.py"))
    with pytest.raises(NotADirectoryError, match="is not a directory") as excinfo:
        _ = get_lib()

    assert str((tmp_path / "lib").resolve()) in str(excinfo.value)


## The suffix of shared libraries on the current platform
LIB_SUFFIX = ".dll" if sys.platform.startswith("win") else ".dylib" if sys.platform == "darwin" else ".so"


def test_get_libpath_finds_pyeq36() -> None:
    """Ensure that `get_libpath` finds the bundled `pyeq36` library."""
    assert get_libpath("pyeq36") == get_lib() / f"libpyeq36{LIB_SUFFIX}"


@pytest.fixture
def lib_dir(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Path:
    """
    Make `get_lib` return an empty temporary `lib` directory.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory in which to create the `lib` directory

    @return The resolved `lib` directory
    """
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "paths.py"))
    lib = tmp_path / "lib"
    lib.mkdir()
    return lib.resolve()


@pytest.mark.parametrize(
    ("platform", "lib", "expected"),
    [
        ("linux", "pyeq36", "libpyeq36.so"),
        ("linux", "libpyeq36", "libpyeq36.so"),
        ("linux", "pyeq36.so", "libpyeq36.so"),
        ("linux", "libpyeq36.so", "libpyeq36.so"),
        ("linux", Path("pyeq36"), "libpyeq36.so"),
        ("darwin", "pyeq36", "libpyeq36.dylib"),
        ("darwin", "libpyeq36.dylib", "libpyeq36.dylib"),
        ("win32", "pyeq36", "libpyeq36.dll"),
        ("win32", "pyeq36.dll", "libpyeq36.dll"),
        ("freebsd14", "pyeq36", "libpyeq36"),
    ],
)
def test_get_libpath_names_library_for_platform(
    monkeypatch: pytest.MonkeyPatch,
    lib_dir: Path,
    platform: str,
    lib: str | Path,
    expected: str,
) -> None:
    """
    Ensure that `get_libpath` adds the `lib` prefix and the platform's suffix only where they are missing.

    On unrecognized platforms, no suffix is added.

    @param monkeypatch The pytest monkeypatch fixture
    @param lib_dir     The temporary `lib` directory
    @param platform    The value of `sys.platform`
    @param lib         The name of the library to search for
    @param expected    The expected filename of the library
    """
    (lib_dir / expected).touch()
    monkeypatch.setattr(sys, "platform", platform)
    assert get_libpath(lib) == lib_dir / expected


def test_get_libpath_searches_subdirectories(monkeypatch: pytest.MonkeyPatch, lib_dir: Path) -> None:
    """
    Ensure that `get_libpath` searches the subdirectory of `lib` given by the parent of the library name.

    @param monkeypatch The pytest monkeypatch fixture
    @param lib_dir     The temporary `lib` directory
    """
    (lib_dir / "sub").mkdir()
    (lib_dir / "sub" / "libpyeq36.so").touch()
    monkeypatch.setattr(sys, "platform", "linux")
    assert get_libpath(Path("sub", "pyeq36")) == lib_dir / "sub" / "libpyeq36.so"


def test_get_libpath_raises_if_not_found(lib_dir: Path) -> None:
    """
    Ensure that `get_libpath` raises a `FileNotFoundError`, naming the path, if the library is not in `lib`.

    @param lib_dir The (empty) temporary `lib` directory
    """
    with pytest.raises(FileNotFoundError, match="library not found") as excinfo:
        _ = get_libpath("pyeq36")

    assert excinfo.value.errno == errno.ENOENT
    assert Path(excinfo.value.filename).parent == lib_dir
    assert str(excinfo.value).count(repr(excinfo.value.filename)) == 1


def test_get_libpath_raises_if_lib_is_missing(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """
    Ensure that `get_libpath` raises a `FileNotFoundError` if the `lib` directory does not exist.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory without a `lib` subdirectory
    """
    monkeypatch.setattr(paths, "__file__", str(tmp_path / "paths.py"))
    with pytest.raises(FileNotFoundError) as excinfo:
        _ = get_libpath("pyeq36")

    assert excinfo.value.filename == str((tmp_path / "lib").resolve())


@pytest.mark.parametrize(
    "filepath",
    [
        "ok.d1",
        Path("dir", "ok.d1"),
        pytest.param(f"{NON_ASCII}.d1", marks=requires_non_ascii),
        pytest.param(Path(NON_ASCII, f"{NON_ASCII}.d1"), marks=requires_non_ascii),
    ],
)
def test_check_encodable_returns_string(filepath: str | Path) -> None:
    """
    Ensure that `check_encodable` returns an encodable filepath as a string.

    The non-ASCII filepaths are skipped if the ANSI code page cannot represent them.

    @param filepath The filepath to check
    """
    assert check_encodable(filepath) == str(filepath)


@pytest.mark.parametrize("filepath", [f"{ANSI_UNENCODABLE}.d1", Path(ANSI_UNENCODABLE, "ok.d1")])
def test_check_encodable_does_not_check_other_platforms(monkeypatch: pytest.MonkeyPatch, filepath: str | Path) -> None:
    """
    Ensure that `check_encodable` returns a filepath unchecked on platforms other than Windows.

    @param monkeypatch The pytest monkeypatch fixture
    @param filepath    A filepath which no ANSI code page other than UTF-8 can represent
    """
    monkeypatch.setattr(sys, "platform", "linux")
    assert check_encodable(filepath) == str(filepath)


@pytest.mark.skipif(not sys.platform.startswith("win"), reason="the ANSI code page is only used on Windows")
@pytest.mark.skipif(ansi_encodable(ANSI_UNENCODABLE), reason="the ANSI code page is UTF-8")
@pytest.mark.parametrize("filepath", [f"{ANSI_UNENCODABLE}.d1", Path(ANSI_UNENCODABLE, "ok.d1")])
def test_check_encodable_raises_on_windows(filepath: str | Path) -> None:
    """
    Ensure that `check_encodable` raises a `UnicodeEncodeError`, naming the filepath, if it is unencodable on Windows.

    @param filepath A filepath which no ANSI code page other than UTF-8 can represent
    """
    with pytest.raises(UnicodeEncodeError) as excinfo:
        _ = check_encodable(filepath)

    assert repr(str(filepath)) in str(excinfo.value)
    assert excinfo.value.object == str(filepath)
    assert isinstance(excinfo.value.__cause__, UnicodeEncodeError)
