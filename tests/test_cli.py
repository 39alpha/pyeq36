"""Test the executable shims in `eq36.cli` without replacing the test process."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from eq36 import cli
from eq36.paths import get_execpath

if TYPE_CHECKING:
    from collections.abc import Callable


@pytest.fixture
def execv_args(monkeypatch: pytest.MonkeyPatch) -> list[tuple[Path, list[str]]]:
    """
    Replace `os.execv` with a stub which records its arguments.

    @param monkeypatch The pytest monkeypatch fixture

    @return A list to which the arguments of each call are appended
    """
    calls: list[tuple[Path, list[str]]] = []

    def stub(path: Path, argv: list[str]) -> None:
        calls.append((path, argv))

    monkeypatch.setattr(cli.os, "execv", stub)
    return calls


@pytest.mark.parametrize(("shim", "executable"), [(cli.eqpt, "eqpt"), (cli.eq3nr, "eq3nr"), (cli.eq6, "eq6")])
def test_shim_execs_executable(
    monkeypatch: pytest.MonkeyPatch,
    execv_args: list[tuple[Path, list[str]]],
    shim: Callable[[], None],
    executable: str,
) -> None:
    """
    Ensure that each shim replaces the process with its executable, passing `sys.argv`.

    @param monkeypatch The pytest monkeypatch fixture
    @param execv_args  The recorded arguments of calls to `os.execv`
    @param shim        The shim under test
    @param executable  The name of the executable that `shim` should run
    """
    argv = [executable, "data1", "input"]
    monkeypatch.setattr(sys, "argv", argv)
    shim()

    assert execv_args == [(get_execpath(executable), argv)]


@pytest.mark.parametrize(("shim", "executable"), [(cli.eqpt, "eqpt"), (cli.eq3nr, "eq3nr"), (cli.eq6, "eq6")])
def test_shim_exits_if_executable_is_missing(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    execv_args: list[tuple[Path, list[str]]],
    shim: Callable[[], None],
    executable: str,
) -> None:
    """
    Ensure that each shim exits with a message, and the process is not replaced, if its executable is not found.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    An empty temporary directory to use as the `bin` directory
    @param execv_args  The recorded arguments of calls to `os.execv`
    @param shim        The shim under test
    @param executable  The name of the executable that `shim` should run
    """
    monkeypatch.setenv("EQ36_BIN", str(tmp_path))
    with pytest.raises(SystemExit) as excinfo:
        shim()

    assert isinstance(excinfo.value.code, str)
    assert excinfo.value.code.startswith(f"{executable}: ")
    assert "command not found" in excinfo.value.code
    assert execv_args == []


def test_shim_exits_if_bin_is_not_a_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    execv_args: list[tuple[Path, list[str]]],
) -> None:
    """
    Ensure that a shim exits with a message, and the process is not replaced, if the `bin` path is not a directory.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory containing a file to use as the `bin` directory
    @param execv_args  The recorded arguments of calls to `os.execv`
    """
    (tmp_path / "file").touch()
    monkeypatch.setenv("EQ36_BIN", str(tmp_path / "file"))
    with pytest.raises(SystemExit) as excinfo:
        cli.eqpt()

    assert isinstance(excinfo.value.code, str)
    assert excinfo.value.code.startswith("eqpt: ")
    assert "from EQ36_BIN is not a directory" in excinfo.value.code
    assert execv_args == []


def test_shim_exits_if_executable_cannot_be_executed(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure that a shim exits with a message if `os.execv` fails.

    @param monkeypatch The pytest monkeypatch fixture
    """

    def execv(_path: Path, _argv: list[str]) -> None:
        raise OSError(8, "Exec format error")

    monkeypatch.setattr(cli.os, "execv", execv)
    with pytest.raises(SystemExit) as excinfo:
        cli.eqpt()

    assert excinfo.value.code == "eqpt: [Errno 8] Exec format error"


def test_shim_exits_on_runtime_error(monkeypatch: pytest.MonkeyPatch, execv_args: list[tuple[Path, list[str]]]) -> None:
    """
    Ensure that a shim exits with a message, and the process is not replaced, if a `RuntimeError` is raised.

    @param monkeypatch The pytest monkeypatch fixture
    @param execv_args  The recorded arguments of calls to `os.execv`
    """

    def get_execpath(_cmd: str) -> Path:
        msg = "something went wrong"
        raise RuntimeError(msg)

    monkeypatch.setattr(cli, "get_execpath", get_execpath)
    with pytest.raises(SystemExit) as excinfo:
        cli.eqpt()

    assert excinfo.value.code == "eqpt: something went wrong"
    assert execv_args == []


def test_shim_propagates_other_errors(
    monkeypatch: pytest.MonkeyPatch, execv_args: list[tuple[Path, list[str]]]
) -> None:
    """
    Ensure that a shim does not handle errors other than `OSError` and `RuntimeError`.

    @param monkeypatch The pytest monkeypatch fixture
    @param execv_args  The recorded arguments of calls to `os.execv`
    """

    def get_execpath(_cmd: str) -> Path:
        msg = "a bug"
        raise TypeError(msg)

    monkeypatch.setattr(cli, "get_execpath", get_execpath)
    with pytest.raises(TypeError, match="a bug"):
        cli.eqpt()

    assert execv_args == []


def test_shim_execs_executable_in_eq36_bin(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    execv_args: list[tuple[Path, list[str]]],
) -> None:
    """
    Ensure that a shim replaces the process with the executable in the directory given by `EQ36_BIN`.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory to use as the `bin` directory
    @param execv_args  The recorded arguments of calls to `os.execv`
    """
    suffix = ".exe" if sys.platform.startswith("win") else ""
    executable = tmp_path / f"eqpt{suffix}"
    executable.touch()
    monkeypatch.setenv("EQ36_BIN", str(tmp_path))
    argv = [str(Path("elsewhere", "eqpt")), "data0"]
    monkeypatch.setattr(sys, "argv", argv)
    cli.eqpt()

    assert execv_args == [(executable.resolve(), argv)]


@pytest.mark.parametrize("platform", [sys.platform, "win32"])
def test_shim_exits_if_executable_is_the_shim(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    execv_args: list[tuple[Path, list[str]]],
    platform: str,
) -> None:
    """
    Ensure that a shim exits with a message, and the process is not replaced, if the executable is the running shim.

    This happens if `EQ36_BIN` is the directory containing the shims. On
    Windows, the executable has an `.exe` suffix but the shims strip it from
    `sys.argv[0]`, so the paths must be compared without it.

    @param monkeypatch The pytest monkeypatch fixture
    @param tmp_path    A temporary directory, containing the shim, to use as the `bin` directory
    @param execv_args  The recorded arguments of calls to `os.execv`
    @param platform    The platform to run on, either the current platform or (faked) Windows
    """
    monkeypatch.setattr(sys, "platform", platform)
    suffix = ".exe" if platform.startswith("win") else ""
    (tmp_path / f"eqpt{suffix}").touch()
    monkeypatch.setenv("EQ36_BIN", str(tmp_path))
    monkeypatch.setattr(sys, "argv", [str(tmp_path / "eqpt"), "data0"])
    with pytest.raises(SystemExit) as excinfo:
        cli.eqpt()

    assert isinstance(excinfo.value.code, str)
    assert excinfo.value.code.startswith("eqpt: ")
    assert "points to a shim script" in excinfo.value.code
    assert execv_args == []
