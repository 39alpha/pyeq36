"""Test the public `eqpt`, `eq3nr` and `eq6` functions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

import eq36
from eq36 import Eq36Error, RunCode, eq3nr, eq6, eqpt
from eq36.paths import get_execpath

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def run_args(monkeypatch: pytest.MonkeyPatch) -> list[tuple[tuple[object, ...], dict[str, object]]]:
    """
    Replace `eq36._run` with a stub which records its arguments.

    @param monkeypatch The pytest monkeypatch fixture

    @return A list to which the positional and keyword arguments of each call are appended
    """
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def stub(*args: object, **kwargs: object) -> tuple[bytes, bytes]:
        calls.append((args, kwargs))
        return b"stdout", b"stderr"

    monkeypatch.setattr(eq36, "_run", stub)
    return calls


@pytest.mark.parametrize("error_check", [True, False])
def test_eqpt_runs_eqpt(run_args: list[tuple[tuple[object, ...], dict[str, object]]], *, error_check: bool) -> None:
    """
    Ensure that `eqpt` runs the `eqpt` executable on the data0 file with the appropriate options.

    @param run_args    The recorded arguments of calls to `eq36._run`
    @param error_check Whether or not to check `stdout` for error messages
    """
    data0 = Path("data0")
    assert eqpt(data0, timeout=10, error_check=error_check) == (b"stdout", b"stderr")
    assert run_args == [
        (
            (get_execpath("eqpt"), "data0"),
            {"timeout": 10, "fname": data0, "code": RunCode.EQPT_ERROR, "error_check": error_check},
        ),
    ]


@pytest.mark.parametrize(
    ("command", "executable", "code"),
    [(eq3nr, "eq3nr", RunCode.EQ3_ERROR), (eq6, "eq6", RunCode.EQ6_ERROR)],
)
def test_eq3nr_and_eq6_run_executable(
    run_args: list[tuple[tuple[object, ...], dict[str, object]]],
    command: Callable[..., tuple[bytes, bytes]],
    executable: str,
    code: RunCode,
) -> None:
    """
    Ensure that `eq3nr` and `eq6` run their executable on the data1 and input files with the appropriate options.

    @param run_args   The recorded arguments of calls to `eq36._run`
    @param command    The function under test
    @param executable The name of the executable that `command` should run
    @param code       The code that `command` should use for errors
    """
    data1, inputfile = Path("data1"), Path("input")
    assert command(data1, inputfile, timeout=10) == (b"stdout", b"stderr")
    assert run_args == [
        (
            (get_execpath(executable), "data1", "input"),
            {"timeout": 10, "fname": inputfile, "code": code},
        ),
    ]


@pytest.mark.parametrize(
    ("command", "args", "code"),
    [
        (eqpt, ("nope.d0",), RunCode.EQPT_ERROR),
        (eq3nr, ("nope.d1", "nope.3i"), RunCode.EQ3_ERROR),
        (eq6, ("nope.d1", "nope.6i"), RunCode.EQ6_ERROR),
    ],
)
def test_commands_raise_on_missing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    command: Callable[..., tuple[bytes, bytes]],
    args: tuple[str, ...],
    code: RunCode,
) -> None:
    """
    Ensure that the EQ3/6 binaries' error messages are raised as an `Eq36Error`.

    The binaries are run in a temporary directory on files that do not exist.
    The first file is reported as missing, and the last file is named in the
    error message.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory in which to run the command
    @param command     The function under test
    @param args        The (missing) files to pass to `command`
    @param code        The code that `command` should use for errors
    """
    monkeypatch.chdir(tmp_path)
    with pytest.raises(Eq36Error, match=f'The file "{args[0]}" does not exist') as excinfo:
        _ = command(*args, timeout=30)

    assert excinfo.value.code == code
    assert str(excinfo.value).endswith(f" in file {args[-1]!r}")
