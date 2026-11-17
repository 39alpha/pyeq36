"""Provide the exceptions raised when running the EQ3/6 binaries."""

from __future__ import annotations

from enum import IntEnum

from typing_extensions import assert_never, override


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
    and `Eq6Error`, as are timeouts (`TimeoutError`).

    @todo Consider extending the hierarchy to errors not specific to running
          the binaries, such as a `Data1Error` for invalid data1 files (see
          `ERRORS.md`).
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


class TimeoutError(Eq36Error, TimeoutError):
    """An error signifying that an EQ3/6 command timed out."""

    def __init__(self, *args: object, code: RunCode | int = RunCode.TIMEOUT) -> None:
        """
        Construct a `TimeoutError` from `args` and a `code`.

        If no `args` are provided, the error message is generated from `code`
        (see `Eq36Error.__str__`).

        @param args Positional arguments passed on to `Eq36Error`; the first, if
                    provided, is used as the error message
        @param code An optional (keyword-only) code identifying the error;
                    defaults to `RunCode.TIMEOUT`
        """
        super().__init__(*args, code=code)


__all__ = [
    "Eq3Error",
    "Eq6Error",
    "Eq36Error",
    "EqptError",
    "RunCode",
    "TimeoutError",
]
