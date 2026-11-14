# ruff: noqa: SLF001
"""
Test the thin wrapper around libpyeq36 in `eq36.libpyeq36`.

The native subroutines are replaced with mocks so that the error handling and
cleanup of `read_data1` can be tested without a data1 file.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol, cast

import pytest

from eq36 import libpyeq36
from eq36.libpyeq36 import read_data1

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


def test_read_data1_raises_if_open_sets_errno(natives: Natives) -> None:
    """
    Ensure that `read_data1` raises a `RuntimeError` if `_open_data1` sets `errno`.

    @param natives The mocked native subroutines
    """

    def side_effect(fname: bytes, data1: object, errno: object, flen: int) -> None:
        open_side_effect(fname, data1, errno, flen)
        set_ref(errno, 1)

    natives.open_data1.side_effect = side_effect
    with pytest.raises(RuntimeError, match="failed to open data1 file"):
        _ = read_data1("fake.d1")

    assert natives.open_data1.call_args.args[0] == b"fake.d1"
    assert natives.open_data1.call_args.args[3] == len(b"fake.d1")
    natives.read_header.assert_not_called()
    natives.close_data1.assert_not_called()


@pytest.mark.parametrize("error", [RuntimeError("open exploded"), OSError("open os error")])
def test_read_data1_wraps_open_exception(natives: Natives, error: Exception) -> None:
    """
    Ensure that `read_data1` wraps exceptions raised by `_open_data1`, and does not close the file.

    @param natives The mocked native subroutines
    @param error   The exception raised by `_open_data1`
    """
    natives.open_data1.side_effect = error
    with pytest.raises(RuntimeError, match="failed to open data1 file") as excinfo:
        _ = read_data1("broken-open.d1")

    natives.open_data1.assert_called_once()
    natives.read_header.assert_not_called()
    natives.close_data1.assert_not_called()
    assert excinfo.value.__cause__ is error


def test_read_data1_raises_if_header_sets_errno(natives: Natives) -> None:
    """
    Ensure that `read_data1` raises a `RuntimeError` if `_read_header` sets `errno`, and closes the file.

    @param natives The mocked native subroutines
    """

    def side_effect(*args: object) -> None:
        set_ref(args[-1], 3)

    natives.read_header.side_effect = side_effect
    with pytest.raises(RuntimeError, match="failed to read data1 header"):
        _ = read_data1("fake.d1")

    natives.open_data1.assert_called_once()
    natives.read_header.assert_called_once()
    natives.read_body.assert_not_called()
    assert closed_unit(natives) == UNIT


def test_read_data1_wraps_header_exception(natives: Natives) -> None:
    """
    Ensure that `read_data1` wraps exceptions raised by `_read_header`, and closes the file.

    @param natives The mocked native subroutines
    """
    error = RuntimeError("header exploded")
    natives.read_header.side_effect = error
    with pytest.raises(RuntimeError, match="failed to read data1 header") as excinfo:
        _ = read_data1("bad-header.d1")

    natives.open_data1.assert_called_once()
    natives.read_header.assert_called_once()
    natives.read_body.assert_not_called()
    assert closed_unit(natives) == UNIT
    assert excinfo.value.__cause__ is error


def test_read_data1_raises_if_body_sets_errno(natives: Natives) -> None:
    """
    Ensure that `read_data1` raises a `RuntimeError` if `_read_body` sets `errno`, and closes the file.

    @param natives The mocked native subroutines
    """

    def side_effect(*args: object) -> None:
        set_ref(args[-1], 99)

    natives.read_body.side_effect = side_effect
    with pytest.raises(RuntimeError, match="failed to read data1 body"):
        _ = read_data1("errno-after-body.d1")

    natives.open_data1.assert_called_once()
    natives.read_header.assert_called_once()
    natives.read_body.assert_called_once()
    assert closed_unit(natives) == UNIT


def test_read_data1_wraps_body_exception(natives: Natives) -> None:
    """
    Ensure that `read_data1` wraps exceptions raised by `_read_body`, and closes the file.

    @param natives The mocked native subroutines
    """
    error = RuntimeError("body exploded")
    natives.read_body.side_effect = error
    with pytest.raises(RuntimeError, match="failed to read data1 body") as excinfo:
        _ = read_data1("bad-body.d1")

    natives.open_data1.assert_called_once()
    natives.read_header.assert_called_once()
    natives.read_body.assert_called_once()
    assert closed_unit(natives) == UNIT
    assert excinfo.value.__cause__ is error


def test_read_data1_raises_on_non_ascii_filename(natives: Natives) -> None:
    """
    Ensure that `read_data1` raises a `UnicodeEncodeError` for a non-ASCII filename before opening it.

    @param natives The mocked native subroutines
    """
    with pytest.raises(UnicodeEncodeError):
        _ = read_data1("μ.d1")

    natives.open_data1.assert_not_called()
