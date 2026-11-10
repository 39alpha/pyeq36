"""Test the detection of errors in the output of EQ3/6 commands."""

from pathlib import Path

import pytest

from eq36 import Eq36Error, RunCode, _error_guard

## The `stdout` of `eqpt` when run on a data0 file that does not exist
MISSING_FILE_OUTPUT = b'\n * Error - (EQLIBU/openin) The file "nope.d0"\n       does not exist.\n'


@pytest.mark.parametrize("output", [b"", "", b"\n * Note - all is well\n", " * Note - all is well"])
def test_error_guard_ignores_output_without_errors(output: bytes | str) -> None:
    """
    Ensure that no error is raised if the output does not contain an error message.

    @param output Command output without an error message
    """
    _error_guard(output, "cmd", code=RunCode.EQPT_ERROR)


@pytest.mark.parametrize("output", [MISSING_FILE_OUTPUT, MISSING_FILE_OUTPUT.decode("utf-8")])
def test_error_guard_raises_on_error(output: bytes | str) -> None:
    """
    Ensure that an error message is found in both `bytes` and `str` output.

    The `"Error"` prefix should be replaced with the command and whitespace,
    including newlines, collapsed.

    @param output Command output containing an error message
    """
    with pytest.raises(Eq36Error) as excinfo:
        _error_guard(output, "eqpt", code=RunCode.EQPT_ERROR)

    assert str(excinfo.value).startswith('eqpt - (EQLIBU/openin) The file "nope.d0" does not exist.')
    assert "\n" not in str(excinfo.value)


@pytest.mark.parametrize("code", [None, 5, RunCode.EQ3_ERROR])
def test_error_guard_uses_code(code: RunCode | int | None) -> None:
    """
    Ensure that the raised error carries the provided code, or `1` if none is provided.

    @param code The code to pass to `_error_guard`
    """
    with pytest.raises(Eq36Error) as excinfo:
        _error_guard(MISSING_FILE_OUTPUT, "eqpt", code=code)

    assert excinfo.value.code == (code if code is not None else 1)


@pytest.mark.parametrize("fname", ["nope.d0", Path("nope.d0")])
def test_error_guard_includes_filename(fname: str | Path) -> None:
    """
    Ensure that the filename, if provided, is included in the error message.

    @param fname The filename to pass to `_error_guard`
    """
    with pytest.raises(Eq36Error) as excinfo:
        _error_guard(MISSING_FILE_OUTPUT, "eqpt", code=RunCode.EQPT_ERROR, fname=fname)

    assert str(excinfo.value).endswith(f" in file {str(fname)!r}")


def test_error_guard_raises_first_error() -> None:
    """Ensure that only the first of several error messages is included in the raised error."""
    output = b"\n * Error - (EQPT/first) The first error.\n\n * Error - (EQPT/second) The second error.\n"
    with pytest.raises(Eq36Error) as excinfo:
        _error_guard(output, "eqpt", code=RunCode.EQPT_ERROR)

    assert "first error" in str(excinfo.value)
    assert "second error" not in str(excinfo.value)


def test_error_guard_skips_empty_errors() -> None:
    """Ensure that error messages without content are skipped in favor of the first non-empty message."""
    output = b"\n * Error - \n\n * Error - (EQPT/real) The real error.\n"
    with pytest.raises(Eq36Error) as excinfo:
        _error_guard(output, "eqpt", code=RunCode.EQPT_ERROR)

    assert str(excinfo.value) == "eqpt - (EQPT/real) The real error."


@pytest.mark.parametrize("output", [b"\n * Error - \n", b"\n * Error - \n\n * Error - \n   \n"])
def test_error_guard_ignores_only_empty_errors(output: bytes) -> None:
    """
    Ensure that no error is raised if every error message is without content.

    @param output Command output containing only empty error messages
    """
    _error_guard(output, "eqpt", code=RunCode.EQPT_ERROR)
