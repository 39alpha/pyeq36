"""
Provide executable shims for the compiled EQ3/6 binaries.

Providing compiled binaries in wheels is somewhat tricky, especially if you want
to support a wide variety of machines (as we do). The
[auditwheel](https://github.com/pypa/auditwheel) tool works wonders and our
initial, naive approach of simply including the binaries as scripts worked
great. It worked by placing the delocated binaries and shared libraries in the
platform directory, installing them next to the main package, and introducing
shims as scripts. However, we ran into issues on MacOS because
[delocate](https://github.com/matthew-brett/delocate) does not automatically
generate the shims.

The simple solution is to include the binaries directly inside our main package
source and then provide our own shims.
"""

import os
import sys
from pathlib import Path

from eq36.paths import check_filepath_compatibility, get_execpath, remove_exe


def _run(cmd: str) -> None:
    """
    Replace the running process with `cmd`, passing `sys.argv`.

    The `cmd` is expected to be an EQ3/6 executable that the `get_execpath`
    function can resolve, e.g. one installed as part of this package or in the
    directory given by `EQ36_BIN`. Arguments from `sys.argv` are passed on to
    the executable.

    If the executable resolves to the running script, e.g. because `EQ36_BIN`
    is the directory containing the shims, the process exits rather than
    endlessly re-running the shim.

    @private

    @param cmd The name of the command to be run, e.g. `"eq6"`

    @warning This function calls `os.execv` which replaces the current running
    process, so it does not return on success. As such, you probably don't
    want to call it from a script unless you're not planning on doing anything
    else.
    """
    try:
        this_script = Path(sys.argv[0]).resolve()
        target = get_execpath(cmd)
        if remove_exe(target) == remove_exe(this_script):
            msg = (
                f"cannot run the target command {str(target)!r} because it points "
                "to a shim script; this is likely because EQ36_BIN was set to the "
                "directory containing the shims"
            )
            sys.exit(f"{cmd}: {msg}")

        os.execv(target, [sys.argv[0], *(check_filepath_compatibility(arg) for arg in sys.argv[1:])])
    except (OSError, RuntimeError, ValueError) as err:
        sys.exit(f"{cmd}: {err}")


def eqpt() -> None:
    """
    Replace the running process with `eqpt`, passing `sys.argv`.

    This is the entry point for the `eqpt` script installed with this package.

    @note If `eqpt` cannot be run, the process exits with status 1, writing a
          message to `stderr`; see `_run`.

    @warning This function does not return on success; see `_run`.
    """
    _run("eqpt")


def eq3nr() -> None:
    """
    Replace the running process with `eq3nr`, passing `sys.argv`.

    This is the entry point for the `eq3nr` script installed with this package.

    @note If `eq3nr` cannot be run, the process exits with status 1, writing a
          message to `stderr`; see `_run`.

    @warning This function does not return on success; see `_run`.
    """
    _run("eq3nr")


def eq6() -> None:
    """
    Replace the running process with `eq6`, passing `sys.argv`.

    This is the entry point for the `eq6` script installed with this package.

    @note If `eq6` cannot be run, the process exits with status 1, writing a
          message to `stderr`; see `_run`.

    @warning This function does not return on success; see `_run`.
    """
    _run("eq6")
