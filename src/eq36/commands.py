"""Provide functions for executing the EQ3/6 binaries from Python, and the errors they raise."""

from __future__ import annotations

import re
import sys
from enum import IntEnum
from functools import partial
from subprocess import PIPE, Popen, TimeoutExpired
from typing import TYPE_CHECKING, Any

from typing_extensions import assert_never, override

from eq36.paths import check_filepath_compatibility, get_execpath

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

    This is the root of the `eq36` exception hierarchy. Errors raised while
    running a particular binary are subclasses, i.e. `EqptError`, `Eq3Error`
    and `Eq6Error`, as are timeouts (`Eq36TimeoutError`).
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


class EqptError(Eq36Error):
    """An error specific to running EQPT."""

    def __init__(self, *args: object, code: RunCode | int = RunCode.EQPT_ERROR) -> None:
        """
        Construct an `EqptError` from `args` and a `code`.

        If no `args` are provided, the error message is generated from `code`
        (see `Eq36Error.__str__`).

        @param args Positional arguments passed on to `Eq36Error`; the first, if
                    provided, is used as the error message
        @param code An optional (keyword-only) code identifying the error;
                    defaults to `RunCode.EQPT_ERROR`
        """
        super().__init__(*args, code=code)


class Eq3Error(Eq36Error):
    """An error specific to running EQ3."""

    def __init__(self, *args: object, code: RunCode | int = RunCode.EQ3_ERROR) -> None:
        """
        Construct an `Eq3Error` from `args` and a `code`.

        If no `args` are provided, the error message is generated from `code`
        (see `Eq36Error.__str__`).

        @param args Positional arguments passed on to `Eq36Error`; the first, if
                    provided, is used as the error message
        @param code An optional (keyword-only) code identifying the error;
                    defaults to `RunCode.EQ3_ERROR`
        """
        super().__init__(*args, code=code)


class Eq6Error(Eq36Error):
    """An error specific to running EQ6."""

    def __init__(self, *args: object, code: RunCode | int = RunCode.EQ6_ERROR) -> None:
        """
        Construct an `Eq6Error` from `args` and a `code`.

        If no `args` are provided, the error message is generated from `code`
        (see `Eq36Error.__str__`).

        @param args Positional arguments passed on to `Eq36Error`; the first, if
                    provided, is used as the error message
        @param code An optional (keyword-only) code identifying the error;
                    defaults to `RunCode.EQ6_ERROR`
        """
        super().__init__(*args, code=code)


class Eq36TimeoutError(Eq36Error):
    """An error signifying that an EQ3/6 command timed out."""

    ## The command that timed out
    cmd: str
    ## The timeout that expired (in seconds)
    timeout: float

    def __init__(self, *args: object, cmd: str | Path, timeout: float, code: RunCode | int = RunCode.TIMEOUT) -> None:
        """
        Construct an `Eq36TimeoutError` from `args`, the command, its timeout and a `code`.

        If no `args` are provided, the error message is generated from `code`
        (see `Eq36Error.__str__`).

        @param args    Positional arguments passed on to `Eq36Error`; the first, if
                       provided, is used as the error message
        @param cmd     The (keyword-only) command that timed out; stored as a `str`
        @param timeout The (keyword-only) timeout that expired (in seconds)
        @param code    An optional (keyword-only) code identifying the error;
                       defaults to `RunCode.TIMEOUT`
        """
        super().__init__(*args, code=code)
        self.cmd = str(cmd)
        self.timeout = timeout

    @override
    # pyrefly: ignore[explicit-any]
    def __reduce__(self) -> tuple[Any, ...]:
        """
        Reduce the error for pickling and copying.

        The error is reconstructed by calling its type with `args` and the
        keyword-only `cmd` and `timeout`, after which the rest of its state,
        e.g. `code`, is restored.

        @return A constructor with `cmd` and `timeout` bound, the arguments with
                which to call it, and the error's state
        """
        return (partial(type(self), cmd=self.cmd, timeout=self.timeout), self.args, self.__dict__)


def _error_guard(output: bytes | str, cmd: str, error_type: type[Eq36Error], fname: str | Path | None = None) -> None:
    """
    Raise an informative error if one is found in the output of a command.

    The output is searched for EQ3/6 error messages, i.e. those beginning with
    `"Error - "`. An error of type `error_type` is raised for the first
    non-empty message, with the `"Error"` prefix replaced by `cmd`.

    @private

    @param output     The output (`stdout`) of the command
    @param cmd        The command that was run
    @param error_type The type of error to raise if an error is encountered
    @param fname      An optional filename to include in any error message

    @throws Eq36Error of type `error_type`, with its default code, if an error
            message is found in the command output
    """
    if isinstance(output, bytes):
        encoding = "mbcs" if sys.platform.startswith("win") else sys.getfilesystemencoding()
        output = output.decode(encoding, errors="replace")

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
    @throws Eq36TimeoutError if the command times out
    @throws OSError if the command cannot be executed
    """
    with Popen([cmd, *args], stdout=PIPE, stderr=PIPE) as process:
        try:
            stdout, stderr = process.communicate(timeout=timeout)
            if error_check:
                _error_guard(stdout, str(cmd), error_type, fname=fname)
        except TimeoutExpired as terr:
            # The only way to land here is for timeout to not be None and for the
            # process to actually time out.
            assert timeout is not None

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
                    raise Eq36TimeoutError(msg, cmd=cmd, timeout=timeout) from e

                raise Eq36TimeoutError(msg, cmd=cmd, timeout=timeout) from terr

            msg = f"{cmd} timed out"
            if fname is not None:
                msg += f" on file {fname!r}"
            raise Eq36TimeoutError(msg, cmd=cmd, timeout=timeout) from terr
        except BaseException:
            process.kill()
            raise

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
    @throws Eq36TimeoutError if the command times out
    @throws FileNotFoundError if the `bin` directory does not exist
    @throws NotADirectoryError if the `bin` path is not a directory
    @throws FileNotFoundError if the `eqpt` executable is not found
    @throws UnicodeEncodeError if a filepath cannot be encoded, e.g. on Windows if the ANSI code page cannot
            represent it
    @throws ValueError if a filepath is longer than `MAX_FILEPATH_BYTES` bytes once encoded
    @throws OSError if the executable cannot be executed
    """
    return _run(
        get_execpath("eqpt"),
        check_filepath_compatibility(data0),
        timeout=timeout,
        fname=data0,
        error_type=EqptError,
        error_check=error_check,
    )


def eq3nr(
    data1: str | Path,
    threei: str | Path,
    timeout: float | None = None,
    error_check: bool = True,
) -> tuple[bytes, bytes]:
    """
    Run `eq3nr` on a data1 and a 3i file.

    All generated files are left in the current working directory, even if an
    error occurs.

    @param data1       The filepath of an EQ3/6 data1 file
    @param threei      The filepath of an EQ3NR input (3i) file
    @param timeout     An optional timeout for the command (in seconds)
    @param error_check Whether or not to check the output of the command for errors

    @return A tuple of the `stdout` and `stderr` output of the command

    @throws Eq3Error if `stdout` includes an error message and `error_check == True`
    @throws Eq3Error with the process' exit code if the command exits with a non-zero exit code (e.g. segfaults)
    @throws Eq36TimeoutError if the command times out
    @throws FileNotFoundError if the `bin` directory does not exist
    @throws NotADirectoryError if the `bin` path is not a directory
    @throws FileNotFoundError if the `eq3nr` executable is not found
    @throws UnicodeEncodeError if a filepath cannot be encoded, e.g. on Windows if the ANSI code page cannot
            represent it
    @throws ValueError if a filepath is longer than `MAX_FILEPATH_BYTES` bytes once encoded
    @throws OSError if the executable cannot be executed
    """
    return _run(
        get_execpath("eq3nr"),
        check_filepath_compatibility(data1),
        check_filepath_compatibility(threei),
        timeout=timeout,
        fname=threei,
        error_type=Eq3Error,
        error_check=error_check,
    )


def eq6(
    data1: str | Path,
    sixi: str | Path,
    timeout: float | None = None,
    error_check: bool = True,
) -> tuple[bytes, bytes]:
    """
    Run `eq6` on a data1 and a 6i file.

    All generated files are left in the current working directory, even if an
    error occurs.

    @param data1       The filepath of an EQ3/6 data1 file
    @param sixi        The filepath of an EQ6 input (6i) file
    @param timeout     An optional timeout for the command (in seconds)
    @param error_check Whether or not to check the output of the command for errors

    @return A tuple of the `stdout` and `stderr` output of the command

    @throws Eq6Error if `stdout` includes an error message and `error_check == True`
    @throws Eq6Error with the process' exit code if the command exits with a non-zero exit code (e.g. segfaults)
    @throws Eq36TimeoutError if the command times out
    @throws FileNotFoundError if the `bin` directory does not exist
    @throws NotADirectoryError if the `bin` path is not a directory
    @throws FileNotFoundError if the `eq6` executable is not found
    @throws UnicodeEncodeError if a filepath cannot be encoded, e.g. on Windows if the ANSI code page cannot
            represent it
    @throws ValueError if a filepath is longer than `MAX_FILEPATH_BYTES` bytes once encoded
    @throws OSError if the executable cannot be executed
    """
    return _run(
        get_execpath("eq6"),
        check_filepath_compatibility(data1),
        check_filepath_compatibility(sixi),
        timeout=timeout,
        fname=sixi,
        error_type=Eq6Error,
        error_check=error_check,
    )


__all__ = [
    "Eq3Error",
    "Eq6Error",
    "Eq36Error",
    "Eq36TimeoutError",
    "EqptError",
    "RunCode",
    "eq3nr",
    "eq6",
    "eqpt",
]
