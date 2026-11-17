"""Provide EQ3/6 binaries and utilities for calling them from Python."""

from __future__ import annotations

import re
from subprocess import PIPE, Popen, TimeoutExpired
from typing import TYPE_CHECKING

from eq36.exceptions import Eq3Error, Eq6Error, Eq36Error, EqptError, RunCode, TimeoutError
from eq36.paths import get_execpath

if TYPE_CHECKING:
    from pathlib import Path


def _error_guard(output: bytes | str, cmd: str, error_type: type[Eq36Error], fname: str | Path | None = None) -> None:
    """
    Raise an informative error if one is found in the output of a command.

    The output is searched for EQ3/6 error messages, i.e. those beginning with
    `"Error - "`. An error of type `error_type` is raised for the first non-empty
    message, with the `"Error"` prefix replaced by `cmd`.

    @private

    @param output     The output (`stdout`) of the command
    @param cmd        The command that was run
    @param error_type The type of error to raise if an error is encountered
    @param fname      An optional filename to include in any error message

    @throws Eq36Error of type `error_type`, with its default code, if an error
            message is found in the command output
    """
    if isinstance(output, bytes):
        output = output.decode("utf-8", errors="replace")

    matches = re.finditer(r"Error - (.*?)(?:\n\s*\n|\Z)", output, flags=re.DOTALL)
    for match in matches:
        error_msg = " ".join(match.group(1).split())
        if error_msg:
            msg = f"{cmd} - {error_msg}"
            if fname is not None:
                msg += f" in file {str(fname)!r}"
            raise error_type(msg)


def _run(
    cmd: str | Path,
    *args: str,
    timeout: float | None = None,
    error_type: type[Eq36Error],
    fname: str | Path | None = None,
    error_check: bool = True,
) -> tuple[bytes, bytes]:
    """
    Run an EQ3/6 command and return the `stdout` and `stderr` output.

    @private

    @param cmd         The filepath of the command to run
    @param args        Arguments to pass to the command
    @param timeout     An optional timeout for the command (in seconds)
    @param error_type  The type of error to raise if an error is found in `stdout` or the
                       command exits with a non-zero exit code
    @param fname       An optional filename to include in any generated error messages
    @param error_check Whether or not to check `stdout` for error messages

    @return A tuple of the `stdout` and `stderr` output of the command

    @throws Eq36Error of type `error_type` if `stdout` includes an error message and `error_check == True`
    @throws Eq36Error of type `error_type` with the process' exit code if the command exits with a
            non-zero exit code (e.g. segfaults)
    @throws TimeoutError if the command times out
    @throws OSError if the command cannot be executed
    """
    process = Popen([cmd, *args], stdout=PIPE, stderr=PIPE)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        if error_check:
            _error_guard(stdout, str(cmd), error_type, fname=fname)
    except TimeoutExpired as terr:
        process.kill()
        stdout, stderr = process.communicate()
        if error_check:
            try:
                _error_guard(stdout, str(cmd), error_type, fname=fname)
                msg = f"{cmd} timed out without errors"
                if fname is not None:
                    msg += f" in file {fname!r}"
            except Eq36Error as e:
                msg = f"{cmd} timed out with errors"
                if fname is not None:
                    msg += f" in file {fname!r}"
                raise TimeoutError(msg) from e

            raise TimeoutError(msg) from terr

        msg = f"{cmd} timed out"
        if fname is not None:
            msg += f" on file {fname!r}"
        raise TimeoutError(msg) from terr

    if process.returncode != 0:
        msg = f"{cmd} failed with an unknown error (code: {process.returncode})"
        raise error_type(msg, code=process.returncode)

    return stdout, stderr


def eqpt(data0: str | Path, timeout: float | None = None, error_check: bool = True) -> tuple[bytes, bytes]:
    """
    Run `eqpt` on a data0 file.

    All generated files are left in the current working directory, even if an
    error occurs.

    @param data0       The filepath of an EQ3/6 data0 file
    @param timeout     An optional timeout for the command (in seconds)
    @param error_check Whether or not to check the output of the command for errors

    @return A tuple of the `stdout` and `stderr` output of the command

    @throws EqptError if `stdout` includes an error message and `error_check == True`
    @throws EqptError with the process' exit code if the command exits with a non-zero exit code (e.g. segfaults)
    @throws TimeoutError if the command times out
    @throws RuntimeError if the `bin` directory does not exist
    @throws RuntimeError if the `eqpt` executable is not found
    @throws OSError if the executable cannot be executed
    """
    return _run(
        get_execpath("eqpt"),
        str(data0),
        timeout=timeout,
        fname=data0,
        error_type=EqptError,
        error_check=error_check,
    )


def eq3nr(data1: str | Path, threei: str | Path, timeout: float | None = None) -> tuple[bytes, bytes]:
    """
    Run `eq3nr` on a data1 and a 3i file.

    All generated files are left in the current working directory, even if an
    error occurs.

    @param data1   The filepath of an EQ3/6 data1 file
    @param threei  The filepath of an EQ3NR input (3i) file
    @param timeout An optional timeout for the command (in seconds)

    @return A tuple of the `stdout` and `stderr` output of the command

    @throws Eq3Error if `stdout` includes an error message
    @throws Eq3Error with the process' exit code if the command exits with a non-zero exit code (e.g. segfaults)
    @throws TimeoutError if the command times out
    @throws RuntimeError if the `bin` directory does not exist
    @throws RuntimeError if the `eq3nr` executable is not found
    @throws OSError if the executable cannot be executed

    @todo Accept `error_check` to disable the error guard.
    """
    return _run(get_execpath("eq3nr"), str(data1), str(threei), timeout=timeout, fname=threei, error_type=Eq3Error)


def eq6(data1: str | Path, sixi: str | Path, timeout: float | None = None) -> tuple[bytes, bytes]:
    """
    Run `eq6` on a data1 and a 6i file.

    All generated files are left in the current working directory, even if an
    error occurs.

    @param data1   The filepath of an EQ3/6 data1 file
    @param sixi    The filepath of an EQ6 input (6i) file
    @param timeout An optional timeout for the command (in seconds)

    @return A tuple of the `stdout` and `stderr` output of the command

    @throws Eq6Error if `stdout` includes an error message
    @throws Eq6Error with the process' exit code if the command exits with a non-zero exit code (e.g. segfaults)
    @throws TimeoutError if the command times out
    @throws RuntimeError if the `bin` directory does not exist
    @throws RuntimeError if the `eq6` executable is not found
    @throws OSError if the executable cannot be executed

    @todo Accept `error_check` to disable the error guard.
    """
    return _run(get_execpath("eq6"), str(data1), str(sixi), timeout=timeout, fname=sixi, error_type=Eq6Error)


__all__ = [
    "Eq3Error",
    "Eq6Error",
    "Eq36Error",
    "EqptError",
    "RunCode",
    "TimeoutError",
    "eq3nr",
    "eq6",
    "eqpt",
]
