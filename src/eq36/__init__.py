"""Provide EQ3/6 binaries and utilities for calling them from Python."""

from __future__ import annotations

import re
from enum import IntEnum
from subprocess import PIPE, Popen, TimeoutExpired
from typing import TYPE_CHECKING

from typing_extensions import assert_never, override

from eq36.paths import get_execpath

if TYPE_CHECKING:
    from pathlib import Path


class RunCode(IntEnum):
    """A code to represent the execution status (exit code) of an EQ3/6 call."""

    ## The command completed without an apparent error.
    SUCCESS = 0
    ## An error occurred while running EQPT
    EQPT_ERROR = 20
    ## An error occurred while running EQ3
    EQ3_ERROR = 30
    ## An error occurred while running EQ6
    EQ6_ERROR = 60
    ## The command timed out
    TIMEOUT = 90

    def __str__(self) -> str:
        """
        Format a `RunCode` as a string for error messages.

        @return A human-readable description of the code
        """
        match self:
            case RunCode.SUCCESS:
                return "success"
            case RunCode.EQPT_ERROR:
                return "eqpt failed with an error"
            case RunCode.EQ3_ERROR:
                return "eq3 failed with an error"
            case RunCode.EQ6_ERROR:
                return "eq6 failed with an error"
            case RunCode.TIMEOUT:
                return "command timed out"
            case _:
                assert_never(self)


class Eq36Error(Exception):
    """
    An error specific to running EQ3/6 binaries.

    @todo Consider introducing an exception hierarchy, rooted at `Eq36Error`,
          in lieu of distinguishing errors by `RunCode`, e.g. subclasses for
          errors in `eqpt`, `eq3nr` and `eq6`, and for timeouts. The hierarchy
          could also include errors not specific to running the binaries, such
          as a `Data1Error` for invalid data1 files (see `ERRORS.md`).
    """

    ## The code identifying the error, either a `RunCode` or a process exit code
    code: RunCode | int

    def __init__(self, *args: object, code: RunCode | int | None = None) -> None:
        """
        Construct an `Eq36Error` from `args` and a `code`.

        @param args Positional arguments passed on to `Exception`; the first, if
                    provided, is used as the error message
        @param code An optional (keyword-only) code identifying the error;
                    defaults to `1`
        """
        super().__init__(*args)
        self.code = code if code is not None else 1

    @override
    def __str__(self) -> str:
        """
        Render the error as a string.

        If the error is initialized with a message, that is returned. Otherwise
        the code is used to generate an error message: known `RunCode` values
        are rendered via `RunCode.__str__`, and any other code is reported as
        an unknown error.

        @return The error message
        """
        if self.args:
            return str(self.args[0])

        if isinstance(self.code, IntEnum):
            return str(self.code)

        try:
            return str(RunCode(self.code))
        except ValueError:
            return f"failed with an unknown error (code: {self.code})"


def _error_guard(output: bytes | str, cmd: str, code: RunCode | int | None, fname: str | Path | None = None) -> None:
    """
    Raise an informative error if one is found in the output of a command.

    The output is searched for EQ3/6 error messages, i.e. those beginning with
    `"Error - "`. An `Eq36Error` is raised for the first non-empty message, with
    the `"Error"` prefix replaced by `cmd`.

    @private

    @param output The output (`stdout`) of the command
    @param cmd    The command that was run
    @param code   An optional code to use if an error is encountered
    @param fname  An optional filename to include in any error message

    @throws Eq36Error if an error message is found in the command output
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
            raise Eq36Error(msg, code=code)


def _run(
    cmd: str | Path,
    *args: str,
    timeout: float | None = None,
    code: RunCode | int | None = None,
    fname: str | Path | None = None,
    error_check: bool = True,
) -> tuple[bytes, bytes]:
    """
    Run an EQ3/6 command and return the `stdout` and `stderr` output.

    @private

    @param cmd         The filepath of the command to run
    @param args        Arguments to pass to the command
    @param timeout     An optional timeout for the command (in seconds)
    @param code        An optional error code to use if an error is found in `stdout`
    @param fname       An optional filename to include in any generated error messages
    @param error_check Whether or not to check `stdout` for error messages

    @return A tuple of the `stdout` and `stderr` output of the command

    @throws Eq36Error with `code` if `stdout` includes an error message and `error_check == True`
    @throws Eq36Error with the process' exit code if the command exits with a non-zero exit code (e.g. segfaults)
    @throws Eq36Error with `RunCode.TIMEOUT` if the command times out
    @throws OSError if the command cannot be executed
    """
    process = Popen([cmd, *args], stdout=PIPE, stderr=PIPE)
    try:
        stdout, stderr = process.communicate(timeout=timeout)
        if error_check:
            _error_guard(stdout, str(cmd), code=code, fname=fname)
    except TimeoutExpired as terr:
        process.kill()
        stdout, stderr = process.communicate()
        if error_check:
            try:
                _error_guard(stdout, str(cmd), code=code, fname=fname)
                msg = f"{cmd} timed out without errors"
                if fname is not None:
                    msg += f" in file {fname!r}"
            except Eq36Error as e:
                msg = f"{cmd} timed out with errors"
                if fname is not None:
                    msg += f" in file {fname!r}"
                raise Eq36Error(msg, code=RunCode.TIMEOUT) from e

            raise Eq36Error(msg, code=RunCode.TIMEOUT) from terr

        msg = f"{cmd} timed out"
        if fname is not None:
            msg += f" on file {fname!r}"
        raise Eq36Error(msg, code=RunCode.TIMEOUT) from terr

    if process.returncode != 0:
        raise Eq36Error(code=process.returncode)

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

    @throws Eq36Error with `RunCode.EQPT_ERROR` if `stdout` includes an error message and `error_check == True`
    @throws Eq36Error with the process' exit code if the command exits with a non-zero exit code (e.g. segfaults)
    @throws Eq36Error with `RunCode.TIMEOUT` if the command times out
    @throws RuntimeError if the package `bin` directory does not exist
    @throws Exception if the `eqpt` executable is not found
    """
    return _run(
        get_execpath("eqpt"),
        str(data0),
        timeout=timeout,
        fname=data0,
        code=RunCode.EQPT_ERROR,
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

    @throws Eq36Error with `RunCode.EQ3_ERROR` if `stdout` includes an error message
    @throws Eq36Error with the process' exit code if the command exits with a non-zero exit code (e.g. segfaults)
    @throws Eq36Error with `RunCode.TIMEOUT` if the command times out
    @throws RuntimeError if the package `bin` directory does not exist
    @throws Exception if the `eq3nr` executable is not found
    """
    return _run(get_execpath("eq3nr"), str(data1), str(threei), timeout=timeout, fname=threei, code=RunCode.EQ3_ERROR)


def eq6(data1: str | Path, sixi: str | Path, timeout: float | None = None) -> tuple[bytes, bytes]:
    """
    Run `eq6` on a data1 and a 6i file.

    All generated files are left in the current working directory, even if an
    error occurs.

    @param data1   The filepath of an EQ3/6 data1 file
    @param sixi    The filepath of an EQ6 input (6i) file
    @param timeout An optional timeout for the command (in seconds)

    @return A tuple of the `stdout` and `stderr` output of the command

    @throws Eq36Error with `RunCode.EQ6_ERROR` if `stdout` includes an error message
    @throws Eq36Error with the process' exit code if the command exits with a non-zero exit code (e.g. segfaults)
    @throws Eq36Error with `RunCode.TIMEOUT` if the command times out
    @throws RuntimeError if the package `bin` directory does not exist
    @throws Exception if the `eq6` executable is not found
    """
    return _run(get_execpath("eq6"), str(data1), str(sixi), timeout=timeout, fname=sixi, code=RunCode.EQ6_ERROR)
