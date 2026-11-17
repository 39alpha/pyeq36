# ruff: noqa: SLF001
"""
Test the thin wrapper around libpyeq36 in `eq36.libpyeq36`.

The native subroutines are replaced with mocks so that the error handling and
cleanup of `read_data1` can be tested without a data1 file.
"""

from __future__ import annotations

import errno
import os
from ctypes import ArgumentError
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Protocol, cast

import pytest

from eq36 import libpyeq36
from eq36.libpyeq36 import Data1Error, read_data1

if TYPE_CHECKING:
    from ctypes import c_int
    from unittest.mock import MagicMock

    from pytest_mock import MockerFixture

## The logical unit "opened" by the mocked `_open_data1`
UNIT = 7

## The array allocation sizes "read" by the mocked `_read_header`, by argument index
HEADER_SIZES = [
    (1, 1),  # ikta_asv
    (2, 1),  # ipbt_asv
    (3, 1),  # ipch_asv
    (4, 1),  # ipcv_asv
    (5, 1),  # jpfc_asv
    (6, 1),  # napa_asv
    (7, 1),  # narx_asv
    (8, 1),  # nata_asv
    (9, 1),  # nbta_asv
    (10, 1),  # ncta_asv
    (11, 1),  # ngta_asv
    (12, 1),  # nlta_asv
    (13, 1),  # nmta_asv
    (14, 1),  # npta_asv
    (15, 1),  # nmuta_asv
    (16, 1),  # nslta_asv
    (17, 1),  # nsta_asv
    (18, 1),  # ntid_asv
    (19, 2),  # ntpr_asv
    (20, 1),  # nxta_asv
]


class Ref(Protocol):
    """The result of `ctypes.byref` applied to a `c_int`; the stubs do not expose `_obj`."""

    ## The referenced object
    _obj: c_int


def set_ref(ref: object, value: int) -> None:
    """
    Set the value of the `c_int` referenced by the result of `ctypes.byref`.

    @param ref   The reference, as passed to a native subroutine
    @param value The value to assign
    """
    cast("Ref", ref)._obj.value = value


def open_side_effect(_fname: bytes, data1: object, _errno: object, _flen: int) -> None:
    """
    Stand in for `_open_data1`, successfully "opening" `UNIT`.

    @param _fname The (unused) encoded filename
    @param data1  A reference to the logical unit
    @param _errno A (unused) reference to the error code
    @param _flen  The (unused) length of the filename
    """
    set_ref(data1, UNIT)


def header_side_effect(*args: object) -> None:
    """
    Stand in for `_read_header`, successfully "reading" `HEADER_SIZES`.

    @param args The arguments to `_read_header`
    """
    for i, value in HEADER_SIZES:
        set_ref(args[i], value)
    set_ref(args[-1], 0)


@dataclass
class Natives:
    """The mocked native subroutines of `eq36.libpyeq36`."""

    ## The mock of `_open_data1`
    open_data1: MagicMock
    ## The mock of `_read_header`
    read_header: MagicMock
    ## The mock of `_read_body`
    read_body: MagicMock
    ## The mock of `_close_data1`
    close_data1: MagicMock


@pytest.fixture
def natives(mocker: MockerFixture) -> Natives:
    """
    Replace the native subroutines of `eq36.libpyeq36` with mocks.

    By default, the mocks successfully open `UNIT`, read `HEADER_SIZES` and
    read the body (leaving the arrays zeroed). Tests override the side effects
    to simulate failures.

    @param mocker The pytest-mock mocker fixture

    @return The mocks
    """
    return Natives(
        open_data1=mocker.patch.object(libpyeq36, "_open_data1", side_effect=open_side_effect),
        read_header=mocker.patch.object(libpyeq36, "_read_header", side_effect=header_side_effect),
        read_body=mocker.patch.object(libpyeq36, "_read_body"),
        close_data1=mocker.patch.object(libpyeq36, "_close_data1"),
    )


def closed_unit(natives: Natives) -> int:
    """
    Get the logical unit passed to the (single) call of `_close_data1`.

    @param natives The mocked native subroutines

    @return The logical unit
    """
    natives.close_data1.assert_called_once()
    return cast("c_int", natives.close_data1.call_args.args[0]).value


def test_read_data1_returns_data(natives: Natives) -> None:
    """
    Ensure that `read_data1` reads the header and body, closes the file and returns the data.

    @param natives The mocked native subroutines
    """
    data = read_data1("ok.d1")

    natives.open_data1.assert_called_once()
    natives.read_header.assert_called_once()
    natives.read_body.assert_called_once()
    assert closed_unit(natives) == UNIT
    assert float(data.min_temperature) == 0.0
    assert data.max_temperature_range.tolist() == [0.0, 0.0]
    assert int(data.first_solid_solution_index) == -1
    assert int(data.last_solid_solution_index) == -1


@pytest.mark.parametrize(
    ("errnum", "error_type", "error_code"),
    [
        (404, FileNotFoundError, errno.ENOENT),
        (403, OSError, errno.EIO),
        (1, OSError, errno.EIO),
    ],
)
def test_read_data1_raises_if_open_sets_errno(
    natives: Natives,
    errnum: int,
    error_type: type[OSError],
    error_code: int,
) -> None:
    """
    Ensure that `read_data1` raises an `OSError`, naming the file, if `_open_data1` sets `errno`, and does not close it.

    `openin` sets `errno` to 404 if the file does not exist and 403 if it
    exists but cannot be opened.

    @param natives    The mocked native subroutines
    @param errnum     The error code set by `_open_data1`
    @param error_type The exact type of the error expected
    @param error_code The `errno` of the error expected
    """

    def side_effect(fname: bytes, data1: object, err: object, flen: int) -> None:
        open_side_effect(fname, data1, err, flen)
        set_ref(err, errnum)

    natives.open_data1.side_effect = side_effect
    with pytest.raises(OSError, match="failed to open data1 file") as excinfo:
        _ = read_data1("fake.d1")

    assert type(excinfo.value) is error_type
    assert excinfo.value.errno == error_code
    assert excinfo.value.filename == "fake.d1"
    natives.read_header.assert_not_called()
    natives.close_data1.assert_not_called()


def test_read_data1_propagates_open_exception(natives: Natives) -> None:
    """
    Ensure that `read_data1` does not wrap exceptions raised by `_open_data1`, and does not close the file.

    @param natives The mocked native subroutines
    """
    error = ArgumentError("open exploded")
    natives.open_data1.side_effect = error
    with pytest.raises(ArgumentError) as excinfo:
        _ = read_data1("broken-open.d1")

    assert excinfo.value is error
    natives.read_header.assert_not_called()
    natives.close_data1.assert_not_called()


def test_read_data1_raises_if_header_sets_errno(natives: Natives) -> None:
    """
    Ensure that `read_data1` raises a `Data1Error`, naming the file, if `_read_header` sets `errno`, and closes it.

    `indath` sets `errno` to 420 if the file is not a data1 file.

    @param natives The mocked native subroutines
    """

    def side_effect(*args: object) -> None:
        set_ref(args[-1], 420)

    natives.read_header.side_effect = side_effect
    with pytest.raises(Data1Error, match=r"not a data1 file: fake\.d1"):
        _ = read_data1("fake.d1")

    natives.read_body.assert_not_called()
    assert closed_unit(natives) == UNIT


def test_read_data1_raises_if_body_sets_errno(natives: Natives) -> None:
    """
    Ensure that `read_data1` raises a `Data1Error`, naming the file, if `_read_body` sets `errno`, and closes it.

    `indata` sets `errno` to the number of errors encountered.

    @param natives The mocked native subroutines
    """

    def side_effect(*args: object) -> None:
        set_ref(args[-1], 99)

    natives.read_body.side_effect = side_effect
    with pytest.raises(Data1Error, match=r"failed to read data1 body: errno-after-body\.d1"):
        _ = read_data1("errno-after-body.d1")

    assert closed_unit(natives) == UNIT


@pytest.mark.parametrize("subroutine", ["read_header", "read_body"])
def test_read_data1_propagates_read_exception(natives: Natives, subroutine: str) -> None:
    """
    Ensure that `read_data1` does not wrap exceptions raised while reading, and closes the file.

    @param natives    The mocked native subroutines
    @param subroutine The name of the mocked subroutine which raises
    """
    error = ArgumentError(f"{subroutine} exploded")
    cast("MagicMock", getattr(natives, subroutine)).side_effect = error
    with pytest.raises(ArgumentError) as excinfo:
        _ = read_data1("bad.d1")

    assert excinfo.value is error
    assert closed_unit(natives) == UNIT


def test_data1_error_is_a_value_error() -> None:
    """Ensure that a `Data1Error` is caught as a `ValueError`."""
    assert issubclass(Data1Error, ValueError)


@pytest.mark.parametrize("filename", ["ok.d1", "μ.d1", Path("μ.d1")])
def test_read_data1_encodes_filename(natives: Natives, filename: str | Path) -> None:
    """
    Ensure that `read_data1` passes the filename to `_open_data1` encoded with `os.fsencode`, with its length in bytes.

    @param natives  The mocked native subroutines
    @param filename The filename to read, which may contain non-ASCII characters
    """
    _ = read_data1(filename)

    fname = os.fsencode(filename)
    natives.open_data1.assert_called_once()
    args = natives.open_data1.call_args.args
    assert args[0] == fname
    assert args[-1] == len(fname)
