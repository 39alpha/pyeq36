"""Ensure that `Eq36Error` exceptions are useful."""

import pytest

from eq36 import Eq36Error, RunCode


def test_instantiate_eq36error_without_code() -> None:
    """Ensure that an `Eq36Error` can be instantiated without a code, defaulting to `1`."""
    err = Eq36Error("message")

    assert str(err) == "message"
    assert err.code == 1


def test_instantiate_eq36error_from_an_int() -> None:
    """Ensure that an `Eq36Error` can be instantiated from an `int` code."""
    code = 5
    err = Eq36Error("message", code=code)

    assert str(err) == "message"
    assert err.code == code


def test_instantiate_eq36error_from_a_runcode() -> None:
    """Ensure that an `Eq36Error` can be instantiated from a `RunCode`."""
    code = RunCode.EQ6_ERROR
    err = Eq36Error("message", code=code)

    assert str(err) == "message"
    assert err.code == code


@pytest.mark.parametrize("code", list(RunCode))
def test_eq36error_str_from_runcode(code: RunCode) -> None:
    """
    Ensure that an `Eq36Error` without a message is rendered using its `RunCode`.

    @param code A `RunCode` instance
    """
    assert str(Eq36Error(code=code)) == str(code)


@pytest.mark.parametrize("code", list(RunCode))
def test_eq36error_str_from_runcode_value(code: RunCode) -> None:
    """
    Ensure that an `Eq36Error` without a message is rendered using the `RunCode` with the same value as its code.

    @param code A `RunCode` instance whose integer value is used as the code
    """
    assert str(Eq36Error(code=int(code))) == str(code)


@pytest.mark.parametrize("code", [1, -11, 255])
def test_eq36error_str_from_unknown_code(code: int) -> None:
    """
    Ensure that an `Eq36Error` without a message is rendered as an unknown error if its code is not a `RunCode`.

    @param code An integer code that does not correspond to a `RunCode`
    """
    assert str(Eq36Error(code=code)) == f"failed with an unknown error (code: {code})"


def test_eq36error_str_without_message_or_code() -> None:
    """Ensure that an `Eq36Error` without a message or code is rendered as an unknown error with code `1`."""
    assert str(Eq36Error()) == "failed with an unknown error (code: 1)"


def test_eq36error_message_takes_precedence_over_code() -> None:
    """Ensure that an `Eq36Error` with both a message and a code is rendered using the message."""
    assert str(Eq36Error("message", code=RunCode.TIMEOUT)) == "message"
