"""
Test that importing `eq36.libpyeq36` fails with an `ImportError` if the library cannot be loaded.

Each test removes `eq36.libpyeq36` (and `eq36.data1`) from `sys.modules`, so
that it is imported afresh while its dependencies are patched. The original
modules are restored afterwards.
"""

from __future__ import annotations

import ctypes
import errno
import importlib
import sys
from pathlib import Path
from typing import TYPE_CHECKING, NoReturn

import pytest

from eq36 import paths

if TYPE_CHECKING:
    from collections.abc import Callable

## The path at which the library is "found" when `get_libpath` is patched
LIBPATH = Path("lib", "libpyeq36.so")


def found_libpath(_lib: str | Path) -> Path:
    """
    Stand in for `get_libpath`, pretending that the library is found.

    @param _lib The name of the library to search for (ignored)

    @return `LIBPATH`
    """
    return LIBPATH


class SymbollessLibrary:
    """
    Stand in for a `CDLL` which has no symbols, as if it was built with different name mangling.

    Like `CDLL`, looking up a symbol either as an attribute or by subscript
    raises an `AttributeError`.
    """

    def __getattr__(self, name: str) -> NoReturn:
        """
        Fail to look up a symbol as an attribute.

        @param name The name of the symbol

        @throws AttributeError always
        """
        msg = f"undefined symbol: {name}"
        raise AttributeError(msg)

    def __getitem__(self, name: str) -> NoReturn:
        """
        Fail to look up a symbol by subscript.

        @param name The name of the symbol

        @throws AttributeError always
        """
        return self.__getattr__(name)


def missing_library(monkeypatch: pytest.MonkeyPatch) -> BaseException:
    """
    Patch `get_libpath` to raise a `FileNotFoundError`, as it does if the library is missing.

    @param monkeypatch The pytest monkeypatch fixture

    @return The error that `get_libpath` raises
    """
    error = FileNotFoundError(errno.ENOENT, "library not found", str(LIBPATH))

    def get_libpath(_lib: str | Path) -> Path:
        raise error

    monkeypatch.setattr(paths, "get_libpath", get_libpath)
    return error


def unloadable_library(monkeypatch: pytest.MonkeyPatch) -> BaseException:
    """
    Patch `CDLL` to raise an `OSError`, as it does if the library cannot be loaded.

    @param monkeypatch The pytest monkeypatch fixture

    @return The error that `CDLL` raises
    """
    error = OSError("libgfortran.so.5: cannot open shared object file")

    def cdll(_name: str) -> object:
        raise error

    monkeypatch.setattr(paths, "get_libpath", found_libpath)
    monkeypatch.setattr(ctypes, "CDLL", cdll)
    return error


def missing_symbol(monkeypatch: pytest.MonkeyPatch) -> BaseException:
    """
    Patch `CDLL` to return a library without symbols, as if it was built with different name mangling.

    @param monkeypatch The pytest monkeypatch fixture

    @return The error raised when a symbol is looked up
    """
    library = SymbollessLibrary()

    def cdll(_name: str) -> object:
        return library

    monkeypatch.setattr(paths, "get_libpath", found_libpath)
    monkeypatch.setattr(ctypes, "CDLL", cdll)
    try:
        _ = library["__pyeq36_data1_MOD_openin"]
    except AttributeError as error:
        return error
    msg = "the patched library unexpectedly has a symbol"
    raise AssertionError(msg)


@pytest.fixture
def fresh_import(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Remove `eq36.libpyeq36` and `eq36.data1` from `sys.modules` until the test ends.

    @param monkeypatch The pytest monkeypatch fixture
    """
    for name in ["eq36.libpyeq36", "eq36.data1"]:
        monkeypatch.delitem(sys.modules, name, raising=False)


@pytest.mark.usefixtures("fresh_import")
@pytest.mark.parametrize(
    "failure",
    [missing_library, unloadable_library, missing_symbol],
    ids=["missing", "unloadable", "missing-symbol"],
)
@pytest.mark.parametrize("module", ["eq36.libpyeq36", "eq36.data1"])
def test_import_raises_import_error(
    monkeypatch: pytest.MonkeyPatch,
    failure: Callable[[pytest.MonkeyPatch], BaseException],
    module: str,
) -> None:
    """
    Ensure that importing a module which loads the library raises an `ImportError`, caused by the original error.

    @param monkeypatch The pytest monkeypatch fixture
    @param failure     A function which patches the loading of the library to fail, returning the expected cause
    @param module      The name of the module to import
    """
    cause = failure(monkeypatch)
    with pytest.raises(ImportError) as excinfo:
        _ = importlib.import_module(module)

    assert excinfo.value.__cause__ is not None
    assert type(excinfo.value.__cause__) is type(cause)
    assert str(excinfo.value.__cause__) == str(cause)
