"""
Test the execution of commands via `eq36._run`.

The Python interpreter running the tests stands in for the EQ3/6 binaries so
that the output, exit code and runtime of the command can be controlled.
"""

import sys

import pytest

from eq36 import Eq36Error, RunCode, _run

## A Python script which writes an EQ3/6-style error message to `stdout`
ERROR_SCRIPT = "print(' * Error - (EQPT/test) Something went wrong.', flush=True)"

## A Python script which takes much longer than the timeouts used in the tests
SLOW_SCRIPT = "import time; time.sleep(30)"


def python(
    script: str,
    *,
    timeout: float | None = None,
    code: RunCode | int | None = None,
    fname: str | None = None,
    error_check: bool = True,
) -> tuple[bytes, bytes]:
    """
    Run a Python script as though it were an EQ3/6 command.

    @param script      The Python source to run
    @param timeout     An optional timeout for the command (in seconds)
    @param code        An optional error code to use if an error is found in `stdout`
    @param fname       An optional filename to include in any generated error messages
    @param error_check Whether or not to check `stdout` for error messages

    @return A tuple of the `stdout` and `stderr` output of the command
    """
    return _run(sys.executable, "-c", script, timeout=timeout, code=code, fname=fname, error_check=error_check)


def test_run_returns_output() -> None:
    """Ensure that `stdout` and `stderr` are returned for a successful command."""
    stdout, stderr = python("import sys; print('out'); print('err', file=sys.stderr)")

    assert stdout.strip() == b"out"
    assert stderr.strip() == b"err"


def test_run_raises_if_command_does_not_exist() -> None:
    """Ensure that an `OSError` is raised if the command cannot be executed."""
    with pytest.raises(OSError):  # noqa: PT011
        _ = _run("/not/an/eq36/executable")


def test_run_raises_on_error_output() -> None:
    """Ensure that an `Eq36Error` with the provided code is raised if `stdout` contains an error message."""
    with pytest.raises(Eq36Error, match="Something went wrong") as excinfo:
        _ = python(ERROR_SCRIPT, code=RunCode.EQPT_ERROR, fname="data0")

    assert excinfo.value.code == RunCode.EQPT_ERROR
    assert str(excinfo.value).endswith(" in file 'data0'")


def test_run_ignores_error_output_without_error_check() -> None:
    """Ensure that error messages in `stdout` are ignored if `error_check` is `False`."""
    stdout, _ = python(ERROR_SCRIPT, code=RunCode.EQPT_ERROR, error_check=False)

    assert b"Something went wrong" in stdout


@pytest.mark.parametrize("error_check", [True, False])
def test_run_raises_on_nonzero_exit_code(*, error_check: bool) -> None:
    """
    Ensure that an `Eq36Error` with the exit code is raised if the command exits with a non-zero exit code.

    @param error_check Whether or not to check `stdout` for error messages
    """
    exit_code = 3
    with pytest.raises(Eq36Error) as excinfo:
        _ = python(f"raise SystemExit({exit_code})", code=RunCode.EQPT_ERROR, error_check=error_check)

    assert excinfo.value.code == exit_code


@pytest.mark.parametrize(
    ("script", "error_check", "message"),
    [
        (SLOW_SCRIPT, True, "timed out without errors"),
        (SLOW_SCRIPT, False, "timed out"),
        (f"{ERROR_SCRIPT}; {SLOW_SCRIPT}", False, "timed out"),
    ],
)
def test_run_raises_on_timeout(script: str, message: str, *, error_check: bool) -> None:
    """
    Ensure that an `Eq36Error` with `RunCode.TIMEOUT` is raised if the command times out.

    @param script      The Python source to run
    @param message     The expected error message, less the command
    @param error_check Whether or not to check `stdout` for error messages
    """
    with pytest.raises(Eq36Error) as excinfo:
        _ = python(script, timeout=0.5, code=RunCode.EQPT_ERROR, error_check=error_check)

    assert excinfo.value.code == RunCode.TIMEOUT
    assert str(excinfo.value) == f"{sys.executable} {message}"


def test_run_raises_on_timeout_with_errors() -> None:
    """Ensure that a timeout reports, and is caused by, any error message found in `stdout`."""
    with pytest.raises(Eq36Error) as excinfo:
        _ = python(f"{ERROR_SCRIPT}; {SLOW_SCRIPT}", timeout=0.5, code=RunCode.EQPT_ERROR)

    assert excinfo.value.code == RunCode.TIMEOUT
    assert str(excinfo.value) == f"{sys.executable} timed out with errors"
    assert isinstance(excinfo.value.__cause__, Eq36Error)
    assert excinfo.value.__cause__.code == RunCode.EQPT_ERROR


@pytest.mark.parametrize(
    ("script", "error_check", "message"),
    [
        (SLOW_SCRIPT, True, "timed out without errors in file 'data0'"),
        (f"{ERROR_SCRIPT}; {SLOW_SCRIPT}", True, "timed out with errors in file 'data0'"),
        (SLOW_SCRIPT, False, "timed out on file 'data0'"),
        (f"{ERROR_SCRIPT}; {SLOW_SCRIPT}", False, "timed out on file 'data0'"),
    ],
)
def test_run_timeout_includes_filename(script: str, message: str, *, error_check: bool) -> None:
    """
    Ensure that the filename, if provided, is included in the timeout error message.

    The filename is reported as the file "in" which errors were, or were not,
    found if `stdout` is checked, and otherwise as the file "on" which the
    command timed out.

    @param script      The Python source to run
    @param message     The expected error message, less the command
    @param error_check Whether or not to check `stdout` for error messages
    """
    with pytest.raises(Eq36Error) as excinfo:
        _ = python(script, timeout=0.5, fname="data0", error_check=error_check)

    assert excinfo.value.code == RunCode.TIMEOUT
    assert str(excinfo.value) == f"{sys.executable} {message}"
