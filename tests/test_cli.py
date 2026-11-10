"""Test the executable shims in `eq36.cli` without replacing the test process."""

from __future__ import annotations

import sys
from typing import TYPE_CHECKING

import pytest

from eq36 import cli
from eq36.paths import get_execpath

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path


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


def test_shim_raises_if_executable_is_missing(execv_args: list[tuple[Path, list[str]]]) -> None:
    """
    Ensure that a `RuntimeError` is raised, and the process is not replaced, if the executable is not found.

    @param execv_args The recorded arguments of calls to `os.execv`
    """
    with pytest.raises(RuntimeError, match="command not found"):
        cli._run("not-an-eq36-executable")  # noqa: SLF001

    assert execv_args == []
