"""
Provide path resolution utilities.

These functions centralize file resolution, e.g. finding the correct binary
executable to be run. By default, the binaries bundled with this package are
used, but the `EQ36_BIN` environment variable can be set to the directory of
EQ3/6 binaries installed elsewhere.
"""

import os
import sys
from pathlib import Path


def remove_exe(path: Path) -> Path:
    """
    Remove the `.exe` suffix, if any, from a path.

    The generated shim scripts strip `.exe` from `sys.argv[0]` on Windows, so
    paths are compared without it.

    @private

    @param path The path from which to remove the suffix

    @return The path without an `.exe` suffix (ignoring case)
    """
    return path.with_suffix("") if path.suffix.lower() == ".exe" else path


def get_bin() -> Path:
    """
    Get the path to the directory containing the EQ3/6 binaries.

    If the `EQ36_BIN` environment variable is set and non-empty, its value is
    used, with `~` expanded and relative paths resolved against the current
    working directory. Otherwise, the `bin` directory bundled with this package
    is used.

    @return The resolved path to the `bin` directory

    @throws RuntimeError if the directory does not exist, noting if the path
            came from `EQ36_BIN`
    """
    path_override = os.getenv("EQ36_BIN")
    if path_override:
        bin_path = Path(path_override).expanduser().resolve()
    else:
        bin_path = (Path(__file__).parent / "bin").resolve()

    if not bin_path.is_dir():
        from_source = " from EQ36_BIN" if path_override else ""
        msg = f"{bin_path}{from_source} is not a directory"
        raise RuntimeError(msg)
    return bin_path


def get_lib() -> Path:
    """
    Get the path to the directory containing the compiled libraries.

    Unlike `get_bin`, this always uses the `lib` directory bundled with this
    package; there is no environment variable override.

    @return The resolved path to the `lib` directory

    @throws RuntimeError if the directory does not exist
    """
    lib_path = (Path(__file__).parent / "lib").resolve()

    if not lib_path.is_dir():
        msg = f"{lib_path} is not a directory"
        raise RuntimeError(msg)
    return lib_path


def get_execpath(cmd: str | Path) -> Path:
    """
    Get the path to an executable in the EQ3/6 `bin` directory.

    The directory is found with `get_bin`, so `EQ36_BIN` is respected. This
    routine ensures that the `cmd` is appropriately suffixed with `'.exe'` on
    Windows machines.

    @param cmd The name of the command to search for, e.g. `"eq6"`

    @return The resolved path to the executable

    @throws RuntimeError if the `bin` directory does not exist
    @throws RuntimeError if the executable is not found in the `bin` directory
    """
    suffix = ".exe" if sys.platform.startswith("win") and not str(cmd).endswith(".exe") else ""
    execpath = (get_bin() / (str(cmd) + suffix)).resolve()
    if not execpath.is_file():
        msg = f"{execpath!s} command not found"
        raise RuntimeError(msg)
    return execpath


def get_libpath(lib: str | Path) -> Path:
    """
    Get the path to a library in the package's `lib` directory.

    The directory is found with `get_lib`. `lib` is resolved relative to that
    directory, so it may name a library in a subdirectory, e.g.
    `"sub/pyeq36"`. The final component of `lib` is prefixed with `"lib"`
    unless it already starts with `"lib"`, and suffixed with `".so"` (Linux),
    `".dylib"` (macOS) or `".dll"` (Windows) unless it already ends with that
    suffix, ignoring case. On any other platform no suffix is added.

    @param lib The name of the library to search for, e.g. `"pyeq36"`

    @return The resolved path to the library

    @throws RuntimeError if the `lib` directory does not exist
    @throws RuntimeError if the library is not found

    @note If `lib` is absolute, or climbs out of the `lib` directory with
          `".."`, the library is searched for at that location instead, so
          this amounts to an existence check (with prefixing and suffixing).
    """
    lib = Path(lib)
    prefix = "lib" if not lib.stem.startswith("lib") else ""

    suffix = ""
    if sys.platform == "linux" and not str(lib).lower().endswith(".so"):
        suffix += ".so"
    elif sys.platform == "darwin" and not str(lib).lower().endswith(".dylib"):
        suffix += ".dylib"
    elif sys.platform.startswith("win") and not str(lib).lower().endswith(".dll"):
        suffix += ".dll"

    libpath = (get_lib() / str(lib.parent) / (prefix + lib.name + suffix)).resolve()
    if not libpath.is_file():
        msg = f"{libpath!s} library not found"
        raise RuntimeError(msg)
    return libpath


__all__ = [
    "get_bin",
    "get_execpath",
    "get_lib",
    "get_libpath",
]
