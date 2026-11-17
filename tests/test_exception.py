"""Ensure that `Eq36Error` exceptions are useful."""

import builtins
import pickle

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from eq36.commands import Eq3Error, Eq6Error, Eq36Error, EqptError, RunCode, TimeoutError

## Each subclass of `Eq36Error` and its default code
SUBCLASSES: list[tuple[type[Eq36Error], RunCode]] = [
    (EqptError, RunCode.EQPT_ERROR),
    (Eq3Error, RunCode.EQ3_ERROR),
    (Eq6Error, RunCode.EQ6_ERROR),
    (TimeoutError, RunCode.TIMEOUT),
]

## `Eq36Error` and each of its subclasses
ERROR_TYPES: list[type[Eq36Error]] = [Eq36Error, *(error_type for error_type, _ in SUBCLASSES)]

## The message of each `RunCode`, keyed by its value
RUNCODE_MESSAGES = {code.value: str(code) for code in RunCode}


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


@given(st.sampled_from(ERROR_TYPES), st.integers())
@example(Eq36Error, 1)
@example(Eq36Error, -11)
@example(Eq36Error, 255)
def test_str_from_any_code(error_type: type[Eq36Error], code: int) -> None:
    """
    Ensure that an error without a message is rendered using its code, whatever its type and code.

    Codes with the value of a `RunCode` are rendered using that `RunCode`, and
    any other code as an unknown error.

    @param error_type The type of the error
    @param code       The code of the error
    """
    expected = RUNCODE_MESSAGES.get(code, f"failed with an unknown error (code: {code})")
    assert str(error_type(code=code)) == expected


def test_eq36error_str_without_message_or_code() -> None:
    """Ensure that an `Eq36Error` without a message or code is rendered as an unknown error with code `1`."""
    assert str(Eq36Error()) == "failed with an unknown error (code: 1)"


def test_eq36error_message_takes_precedence_over_code() -> None:
    """Ensure that an `Eq36Error` with both a message and a code is rendered using the message."""
    assert str(Eq36Error("message", code=RunCode.TIMEOUT)) == "message"


@pytest.mark.parametrize("error_type", [error_type for error_type, _ in SUBCLASSES])
def test_subclass_is_an_eq36error(error_type: type[Eq36Error]) -> None:
    """
    Ensure that each subclass is caught as an `Eq36Error`.

    @param error_type A subclass of `Eq36Error`
    """
    with pytest.raises(Eq36Error):
        raise error_type


@pytest.mark.parametrize(("error_type", "code"), SUBCLASSES)
def test_subclass_default_code(error_type: type[Eq36Error], code: RunCode) -> None:
    """
    Ensure that each subclass defaults to its own code and is rendered using its message.

    @param error_type A subclass of `Eq36Error`
    @param code       The default code of `error_type`
    """
    err = error_type("message")

    assert str(err) == "message"
    assert err.code == code


@pytest.mark.parametrize(("error_type", "code"), SUBCLASSES)
def test_subclass_str_without_message(error_type: type[Eq36Error], code: RunCode) -> None:
    """
    Ensure that each subclass without a message is rendered using its default code.

    @param error_type A subclass of `Eq36Error`
    @param code       The default code of `error_type`
    """
    assert str(error_type()) == str(code)


@pytest.mark.parametrize("error_type", [error_type for error_type, _ in SUBCLASSES])
@pytest.mark.parametrize("code", [5, RunCode.EQ3_ERROR])
def test_subclass_with_custom_code(error_type: type[Eq36Error], code: RunCode | int) -> None:
    """
    Ensure that each subclass accepts a code other than its default.

    The code is retained, and is used to render the error if it has no message.

    @param error_type A subclass of `Eq36Error`
    @param code       A code other than the default code of `error_type`
    """
    with_message = error_type("message", code=code)
    without_message = error_type(code=code)

    assert with_message.code == code
    assert str(with_message) == "message"
    assert without_message.code == code
    assert str(without_message) == str(Eq36Error(code=code))


def test_timeouterror_is_a_builtin_timeouterror() -> None:
    """Ensure that `eq36.commands.TimeoutError` is caught as the built-in `TimeoutError`."""
    with pytest.raises(builtins.TimeoutError):
        raise TimeoutError


def test_timeouterror_is_an_oserror() -> None:
    """
    Ensure that `eq36.commands.TimeoutError` is caught as an `OSError`.

    This follows from it being a built-in `TimeoutError`.
    """
    with pytest.raises(OSError):  # noqa: PT011
        raise TimeoutError


@pytest.mark.parametrize("error_type", ERROR_TYPES)
@pytest.mark.parametrize("args", [(), ("message",)])
@pytest.mark.parametrize("kwargs", [{}, {"code": 5}, {"code": -11}, {"code": RunCode.EQ6_ERROR}])
def test_pickle_roundtrip(error_type: type[Eq36Error], args: tuple[str, ...], kwargs: dict[str, RunCode | int]) -> None:
    """
    Ensure that an error survives pickling with its type, message and code intact.

    @param error_type The type of the error
    @param args       The positional arguments with which to construct the error
    @param kwargs     The keyword arguments with which to construct the error
    """
    err = error_type(*args, **kwargs)
    roundtrip = pickle.loads(pickle.dumps(err))

    assert type(roundtrip) is error_type
    assert roundtrip.args == err.args
    assert roundtrip.code == err.code
    assert str(roundtrip) == str(err)
