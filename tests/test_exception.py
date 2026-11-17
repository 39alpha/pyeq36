"""Ensure that `Eq36Error` exceptions are useful."""

import copy
import pickle
from collections.abc import Callable
from pathlib import Path
from subprocess import TimeoutExpired
from typing import cast

import pytest
from hypothesis import example, given
from hypothesis import strategies as st

from eq36.commands import Eq3Error, Eq6Error, Eq36Error, Eq36TimeoutError, EqptError, RunCode

## Each subclass of `Eq36Error` and its default code
SUBCLASSES: list[tuple[type[Eq36Error], RunCode]] = [
    (EqptError, RunCode.EQPT_ERROR),
    (Eq3Error, RunCode.EQ3_ERROR),
    (Eq6Error, RunCode.EQ6_ERROR),
    (Eq36TimeoutError, RunCode.TIMEOUT),
]

## `Eq36Error` and each of its subclasses
ERROR_TYPES: list[type[Eq36Error]] = [Eq36Error, *(error_type for error_type, _ in SUBCLASSES)]

## The message of each `RunCode`, keyed by its value
RUNCODE_MESSAGES = {code.value: str(code) for code in RunCode}


def construct(error_type: type[Eq36Error], *args: object, code: RunCode | int | None = None) -> Eq36Error:
    """
    Construct an error of any type, supplying any keyword arguments that type requires.

    An `Eq36TimeoutError` is given an arbitrary command and timeout.

    @param error_type The type of the error
    @param args       Positional arguments passed on to `error_type`
    @param code       An optional code for the error; defaults to that of `error_type`

    @return The error
    """
    if error_type is Eq36TimeoutError:
        if code is None:
            return Eq36TimeoutError(*args, cmd="eqpt", timeout=1.0)
        return Eq36TimeoutError(*args, cmd="eqpt", timeout=1.0, code=code)

    if code is None:
        return error_type(*args)
    return error_type(*args, code=code)


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
    assert str(construct(error_type, code=code)) == expected


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
        raise construct(error_type)


@pytest.mark.parametrize(("error_type", "code"), SUBCLASSES)
def test_subclass_default_code(error_type: type[Eq36Error], code: RunCode) -> None:
    """
    Ensure that each subclass defaults to its own code and is rendered using its message.

    @param error_type A subclass of `Eq36Error`
    @param code       The default code of `error_type`
    """
    err = construct(error_type, "message")

    assert str(err) == "message"
    assert err.code == code


@pytest.mark.parametrize(("error_type", "code"), SUBCLASSES)
def test_subclass_str_without_message(error_type: type[Eq36Error], code: RunCode) -> None:
    """
    Ensure that each subclass without a message is rendered using its default code.

    @param error_type A subclass of `Eq36Error`
    @param code       The default code of `error_type`
    """
    assert str(construct(error_type)) == str(code)


@pytest.mark.parametrize("error_type", [error_type for error_type, _ in SUBCLASSES])
@pytest.mark.parametrize("code", [5, RunCode.EQ3_ERROR])
def test_subclass_with_custom_code(error_type: type[Eq36Error], code: RunCode | int) -> None:
    """
    Ensure that each subclass accepts a code other than its default.

    The code is retained, and is used to render the error if it has no message.

    @param error_type A subclass of `Eq36Error`
    @param code       A code other than the default code of `error_type`
    """
    with_message = construct(error_type, "message", code=code)
    without_message = construct(error_type, code=code)

    assert with_message.code == code
    assert str(with_message) == "message"
    assert without_message.code == code
    assert str(without_message) == str(Eq36Error(code=code))


@pytest.mark.parametrize("cmd", ["eqpt", Path("eqpt")])
def test_eq36timeouterror_attributes(cmd: str | Path) -> None:
    """
    Ensure that an `Eq36TimeoutError` retains the command, as a `str`, and the timeout.

    @param cmd The command that timed out
    """
    err = Eq36TimeoutError("message", cmd=cmd, timeout=0.5)

    assert err.cmd == "eqpt"
    assert err.timeout == 0.5  # noqa: PLR2004


@pytest.mark.parametrize("other", [OSError, TimeoutError, TimeoutExpired])
def test_eq36timeouterror_is_only_an_eq36error(other: type[Exception]) -> None:
    """
    Ensure that an `Eq36TimeoutError` is not caught as any other kind of timeout.

    In particular, it is not an `OSError`, which `eq36.commands._run` raises if
    the command cannot be executed.

    @param other An exception type which `Eq36TimeoutError` should not subclass
    """
    assert not issubclass(Eq36TimeoutError, other)


def pickle_roundtrip(err: Eq36Error) -> Eq36Error:
    """
    Duplicate an error by pickling and unpickling it.

    @param err The error to duplicate

    @return The unpickled error
    """
    return cast("Eq36Error", pickle.loads(pickle.dumps(err)))


@pytest.mark.parametrize("duplicate", [pickle_roundtrip, copy.copy, copy.deepcopy], ids=["pickle", "copy", "deepcopy"])
@pytest.mark.parametrize("error_type", ERROR_TYPES)
@pytest.mark.parametrize("args", [(), ("message",)])
@pytest.mark.parametrize("kwargs", [{}, {"code": 5}, {"code": -11}, {"code": RunCode.EQ6_ERROR}])
def test_roundtrip(
    duplicate: Callable[[Eq36Error], Eq36Error],
    error_type: type[Eq36Error],
    args: tuple[str, ...],
    kwargs: dict[str, RunCode | int],
) -> None:
    """
    Ensure that an error survives pickling and copying with its type, message and attributes intact.

    @param duplicate  A function which pickles and unpickles, or copies, an error
    @param error_type The type of the error
    @param args       The positional arguments with which to construct the error
    @param kwargs     The keyword arguments with which to construct the error
    """
    err = construct(error_type, *args, **kwargs)
    roundtrip = duplicate(err)

    assert roundtrip is not err
    assert type(roundtrip) is error_type
    assert roundtrip.args == err.args
    assert vars(roundtrip) == vars(err)
    assert type(roundtrip.code) is type(err.code)
    assert str(roundtrip) == str(err)
