"""Test the public `eqpt`, `eq3nr` and `eq6` functions."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, cast

import pytest

import eq36
from eq36 import Eq3Error, Eq6Error, Eq36Error, EqptError, eq3nr, eq6, eqpt
from eq36.paths import get_execpath

from .ansi import ANSI_UNENCODABLE, ansi_encodable
from .runs import NON_ASCII_STEMS, RUNS, Run, copy_inputs

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def run_args(monkeypatch: pytest.MonkeyPatch) -> list[tuple[tuple[object, ...], dict[str, object]]]:
    """
    Replace `eq36.commands._run` with a stub which records its arguments.

    @param monkeypatch The pytest monkeypatch fixture

    @return A list to which the positional and keyword arguments of each call are appended
    """
    calls: list[tuple[tuple[object, ...], dict[str, object]]] = []

    def stub(*args: object, **kwargs: object) -> tuple[bytes, bytes]:
        calls.append((args, kwargs))
        return b"stdout", b"stderr"

    monkeypatch.setattr(eq36.commands, "_run", stub)
    return calls


@pytest.mark.parametrize("error_check", [True, False])
def test_eqpt_runs_eqpt(run_args: list[tuple[tuple[object, ...], dict[str, object]]], *, error_check: bool) -> None:
    """
    Ensure that `eqpt` runs the `eqpt` executable on the data0 file with the appropriate options.

    @param run_args    The recorded arguments of calls to `eq36.commands._run`
    @param error_check Whether or not to check `stdout` for error messages
    """
    data0 = Path("data0")
    assert eqpt(data0, timeout=10, error_check=error_check) == (b"stdout", b"stderr")
    assert run_args == [
        (
            (get_execpath("eqpt"), "data0"),
            {"timeout": 10, "fname": data0, "error_type": EqptError, "error_check": error_check},
        ),
    ]


@pytest.mark.parametrize("error_check", [True, False])
@pytest.mark.parametrize(
    ("command", "executable", "error_type"),
    [(eq3nr, "eq3nr", Eq3Error), (eq6, "eq6", Eq6Error)],
)
def test_eq3nr_and_eq6_run_executable(
    run_args: list[tuple[tuple[object, ...], dict[str, object]]],
    command: Callable[..., tuple[bytes, bytes]],
    executable: str,
    error_type: type[Eq36Error],
    *,
    error_check: bool,
) -> None:
    """
    Ensure that `eq3nr` and `eq6` run their executable on the data1 and input files with the appropriate options.

    @param run_args    The recorded arguments of calls to `eq36.commands._run`
    @param command     The function under test
    @param executable  The name of the executable that `command` should run
    @param error_type  The type of error that `command` should raise
    @param error_check Whether or not to check `stdout` for error messages
    """
    data1, inputfile = Path("data1"), Path("input")
    assert command(data1, inputfile, timeout=10, error_check=error_check) == (b"stdout", b"stderr")
    assert run_args == [
        (
            (get_execpath(executable), "data1", "input"),
            {"timeout": 10, "fname": inputfile, "error_type": error_type, "error_check": error_check},
        ),
    ]


@pytest.mark.parametrize(
    ("command", "args"), [(eqpt, ("data0",)), (eq3nr, ("data1", "input")), (eq6, ("data1", "input"))]
)
def test_commands_check_errors_by_default(
    run_args: list[tuple[tuple[object, ...], dict[str, object]]],
    command: Callable[..., tuple[bytes, bytes]],
    args: tuple[str, ...],
) -> None:
    """
    Ensure that `eqpt`, `eq3nr` and `eq6` check the output of their executable for errors by default.

    @param run_args The recorded arguments of calls to `eq36.commands._run`
    @param command  The function under test
    @param args     The files to pass to `command`
    """
    _ = command(*args)

    assert len(run_args) == 1
    assert run_args[0][1]["error_check"] is True


@pytest.mark.parametrize(
    ("command", "args", "error_type"),
    [
        (eqpt, ("nope.d0",), EqptError),
        (eq3nr, ("nope.d1", "nope.3i"), Eq3Error),
        (eq6, ("nope.d1", "nope.6i"), Eq6Error),
    ],
)
def test_commands_raise_on_missing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    command: Callable[..., tuple[bytes, bytes]],
    args: tuple[str, ...],
    error_type: type[Eq36Error],
) -> None:
    """
    Ensure that the EQ3/6 binaries' error messages are raised as the error type specific to each binary.

    The binaries are run in a temporary directory on files that do not exist.
    The first file is reported as missing, and the last file is named in the
    error message.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory in which to run the command
    @param command     The function under test
    @param args        The (missing) files to pass to `command`
    @param error_type  The type of error that `command` should raise, with its default code
    """
    monkeypatch.chdir(tmp_path)
    with pytest.raises(error_type, match=f'The file "{args[0]}" does not exist') as excinfo:
        _ = command(*args, timeout=30)

    assert type(excinfo.value) is error_type
    assert excinfo.value.code == error_type().code
    assert str(excinfo.value).endswith(f" in file {args[-1]!r}")


@pytest.mark.parametrize("stem", NON_ASCII_STEMS)
@pytest.mark.parametrize(
    ("command", "extensions"),
    [(eqpt, (".d0",)), (eq3nr, (".d1", ".3i")), (eq6, (".d1", ".6i"))],
    ids=["eqpt", "eq3nr", "eq6"],
)
def test_commands_report_missing_non_ascii_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    command: Callable[..., tuple[bytes, bytes]],
    extensions: tuple[str, ...],
    stem: str,
) -> None:
    """
    Ensure that a missing file with a non-ASCII name is named correctly in the raised error.

    The binaries are run in a temporary directory on files that do not exist,
    and the first file is reported as missing.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory in which to run the command
    @param command     The function under test
    @param extensions  The extensions of the (missing) files to pass to `command`
    @param stem        The non-ASCII stem of the filenames
    """
    args = [f"{stem}{extension}" for extension in extensions]
    monkeypatch.chdir(tmp_path)
    with pytest.raises(Eq36Error) as excinfo:
        _ = command(*args, timeout=30)

    assert f'The file "{args[0]}" does not exist' in str(excinfo.value)


@pytest.mark.parametrize(
    ("command", "args"),
    [(eqpt, ("nope.d0",)), (eq3nr, ("nope.d1", "nope.3i")), (eq6, ("nope.d1", "nope.6i"))],
)
def test_commands_ignore_errors_without_error_check(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    command: Callable[..., tuple[bytes, bytes]],
    args: tuple[str, ...],
) -> None:
    """
    Ensure that the EQ3/6 binaries' error messages are not raised if `error_check` is `False`.

    The binaries are run in a temporary directory on files that do not exist.
    They report the missing file in `stdout` but exit successfully, so the
    output is returned.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory in which to run the command
    @param command     The function under test
    @param args        The (missing) files to pass to `command`
    """
    monkeypatch.chdir(tmp_path)
    stdout, _ = command(*args, timeout=30, error_check=False)

    assert f'The file "{args[0]}"'.encode() in stdout


@pytest.mark.parametrize(
    ("command", "args"),
    [(eqpt, ("data0",)), (eq3nr, ("data1", "input")), (eq6, ("data1", "input"))],
)
def test_commands_raise_if_executable_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    command: Callable[..., tuple[bytes, bytes]],
    args: tuple[str, ...],
) -> None:
    """
    Ensure that `eqpt`, `eq3nr` and `eq6` raise a `FileNotFoundError` if their executable is missing.

    This is the same type that `Popen` raises if it cannot find an executable,
    so callers see one type of error for a missing executable.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    An empty temporary directory to use as the `bin` directory
    @param command     The function under test
    @param args        The files to pass to `command`
    """
    monkeypatch.setenv("EQ36_BIN", str(tmp_path))
    with pytest.raises(FileNotFoundError, match="command not found"):
        _ = command(*args)


@pytest.mark.parametrize("stem", NON_ASCII_STEMS)
@pytest.mark.parametrize("run", RUNS, ids=lambda run: run.executable)
def test_commands_run_files_with_non_ascii_names(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    run: Run,
    stem: str,
) -> None:
    """
    Ensure that `eqpt`, `eq3nr` and `eq6` read and write files with non-ASCII names.

    The test data files are copied into a temporary directory, all named
    `stem`, and the command is run in that directory.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory in which to run the command
    @param run         The command to run, its inputs and the extensions of the files it writes
    @param stem        The non-ASCII stem of the filenames
    """
    command = cast("Callable[..., tuple[bytes, bytes]]", getattr(eq36, run.executable))
    monkeypatch.chdir(tmp_path)
    args = copy_inputs(run.inputs, stem, tmp_path)

    _ = command(*args, timeout=30)

    for extension in run.extensions:
        assert (tmp_path / f"{stem}{extension}").is_file()


class ProcessStartedError(Exception):
    """Raised by the `Popen` stub to stop a command once it would have started a process."""


@pytest.fixture
def popen_args(monkeypatch: pytest.MonkeyPatch) -> list[list[object]]:
    """
    Replace `Popen` in `eq36.commands` with a stub which records its command line and raises `ProcessStartedError`.

    @param monkeypatch The pytest monkeypatch fixture

    @return A list to which the command line of each call is appended
    """
    calls: list[list[object]] = []

    def stub(args: list[object], *_args: object, **_kwargs: object) -> None:
        calls.append(args)
        raise ProcessStartedError

    monkeypatch.setattr(eq36.commands, "Popen", stub)
    return calls


@pytest.mark.parametrize(
    ("command", "args"),
    [
        pytest.param(eqpt, (f"{ANSI_UNENCODABLE}.d0",), id="eqpt"),
        pytest.param(eqpt, (Path(f"{ANSI_UNENCODABLE}.d0"),), id="eqpt-path"),
        pytest.param(eq3nr, (f"{ANSI_UNENCODABLE}.d1", "input.3i"), id="eq3nr-data1"),
        pytest.param(eq3nr, ("data1.d1", f"{ANSI_UNENCODABLE}.3i"), id="eq3nr-input"),
        pytest.param(eq6, (f"{ANSI_UNENCODABLE}.d1", "input.6i"), id="eq6-data1"),
        pytest.param(eq6, ("data1.d1", f"{ANSI_UNENCODABLE}.6i"), id="eq6-input"),
    ],
)
def test_commands_reject_names_the_ansi_code_page_cannot_represent(
    popen_args: list[list[object]],
    command: Callable[..., tuple[bytes, bytes]],
    args: tuple[str | Path, ...],
) -> None:
    """
    Ensure that `eqpt`, `eq3nr` and `eq6` raise `UnicodeEncodeError`, before starting a process, for unencodable names.

    On Windows, the executables receive their arguments in the ANSI code page,
    which replaces characters that it cannot represent with "best fit"
    substitutes, so that the executable would silently open a different file.
    One of the names contains an emoji, which no ANSI code page other than
    UTF-8 can represent. Where the ANSI code page can represent every name,
    i.e. on other platforms or a UTF-8 code page, the names must instead be
    passed on to the executable unchanged.

    @param popen_args The recorded command lines of calls to `Popen`
    @param command    The function under test
    @param args       The files to pass to `command`, one of which contains an emoji
    """
    if all(ansi_encodable(str(arg)) for arg in args):
        with pytest.raises(ProcessStartedError):
            _ = command(*args)

        assert len(popen_args) == 1
        assert popen_args[0][1:] == [str(arg) for arg in args]
    else:
        with pytest.raises(UnicodeEncodeError):
            _ = command(*args)

        assert popen_args == []
