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

from eq36.paths import get_execpath


def _run(cmd: str) -> None:
    """
    Replace the running process with `cmd`, passing `sys.argv`.

    The `cmd` is expected to be an EQ3/6 executable that the `get_execpath`
    function can resolve, e.g. one installed as part of this package. Arguments
    from `sys.argv` are passed on to the executable.

    @private

    @param cmd The name of the command to be run, e.g. `"eq6"`

    @throws RuntimeError if the package `bin` directory does not exist
    @throws Exception if `cmd` is not found in the package `bin` directory
    @throws OSError if the executable cannot be executed

    @warning This function calls `os.execv` which replaces the current running
    process, so it does not return on success. As such, you probably don't
    want to call it from a script unless you're not planning on doing anything
    else.
    """
    os.execv(get_execpath(cmd), sys.argv)


def eqpt() -> None:
    """
    Replace the running process with `eqpt`, passing `sys.argv`.

    This is the entry point for the `eqpt` script installed with this package.

    @throws RuntimeError if the package `bin` directory does not exist
    @throws Exception if `eqpt` is not found in the package `bin` directory
    @throws OSError if the executable cannot be executed

    @warning This function does not return on success; see `_run`.
    """
    _run("eqpt")


def eq3nr() -> None:
    """
    Replace the running process with `eq3nr`, passing `sys.argv`.

    This is the entry point for the `eq3nr` script installed with this package.

    @throws RuntimeError if the package `bin` directory does not exist
    @throws Exception if `eq3nr` is not found in the package `bin` directory
    @throws OSError if the executable cannot be executed

    @warning This function does not return on success; see `_run`.
    """
    _run("eq3nr")


def eq6() -> None:
    """
    Replace the running process with `eq6`, passing `sys.argv`.

    This is the entry point for the `eq6` script installed with this package.

    @throws RuntimeError if the package `bin` directory does not exist
    @throws Exception if `eq6` is not found in the package `bin` directory
    @throws OSError if the executable cannot be executed

    @warning This function does not return on success; see `_run`.
    """
    _run("eq6")
